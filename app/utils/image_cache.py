"""
Image Caching and Static File Optimization System
================================================

Complete static file serving with advanced image caching, compression,
and optimization for maximum performance.
"""

import os
import hashlib
import asyncio
import aiofiles
from typing import Optional, Dict, Any, Union
from datetime import datetime, timedelta
from pathlib import Path
import mimetypes
from PIL import Image
import io
import logging

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, FileResponse
from starlette.middleware.base import BaseHTTPMiddleware

try:
    from .redis_cache import cache
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    cache = None

logger = logging.getLogger(__name__)

class ImageCacheManager:
    """Advanced image caching and optimization"""
    
    def __init__(self, cache_dir: str = "static/cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache settings
        self.max_cache_size = 500 * 1024 * 1024  # 500MB
        self.cache_ttl = 86400 * 7  # 7 days
        
        # Image optimization settings
        self.quality_settings = {
            "webp": 85,
            "jpeg": 85,
            "png": 9  # compression level
        }
        
        # Supported sizes for responsive images
        self.responsive_sizes = [150, 300, 600, 900, 1200]
        
    def get_cache_key(self, image_path: str, width: Optional[int] = None, 
                     height: Optional[int] = None, format: Optional[str] = None) -> str:
        """Generate cache key for image"""
        key_parts = [image_path]
        if width:
            key_parts.append(f"w{width}")
        if height:
            key_parts.append(f"h{height}")
        if format:
            key_parts.append(f"f{format}")
        
        key_string = "_".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def get_cached_path(self, cache_key: str, format: str = "webp") -> Path:
        """Get path for cached image"""
        return self.cache_dir / f"{cache_key}.{format}"
    
    async def optimize_image(self, image_data: bytes, width: Optional[int] = None,
                           height: Optional[int] = None, format: str = "webp",
                           quality: Optional[int] = None) -> bytes:
        """Optimize image with compression and resizing"""
        try:
            # Open image
            image = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB if necessary
            if image.mode in ("RGBA", "P"):
                if format.lower() in ["jpeg", "jpg"]:
                    # Create white background for JPEG
                    background = Image.new("RGB", image.size, (255, 255, 255))
                    if image.mode == "P":
                        image = image.convert("RGBA")
                    background.paste(image, mask=image.split()[-1] if image.mode == "RGBA" else None)
                    image = background
                elif format.lower() == "webp":
                    image = image.convert("RGBA")
            elif image.mode != "RGB" and format.lower() in ["jpeg", "jpg"]:
                image = image.convert("RGB")
            
            # Resize if dimensions specified
            if width or height:
                original_width, original_height = image.size
                
                if width and height:
                    # Exact dimensions
                    new_size = (width, height)
                elif width:
                    # Maintain aspect ratio based on width
                    ratio = width / original_width
                    new_size = (width, int(original_height * ratio))
                else:
                    # Maintain aspect ratio based on height
                    ratio = height / original_height
                    new_size = (int(original_width * ratio), height)
                
                # Use high-quality resampling
                image = image.resize(new_size, Image.Resampling.LANCZOS)
            
            # Save optimized image
            output = io.BytesIO()
            
            if format.lower() == "webp":
                quality = quality or self.quality_settings["webp"]
                image.save(output, format="WebP", quality=quality, optimize=True)
            elif format.lower() in ["jpeg", "jpg"]:
                quality = quality or self.quality_settings["jpeg"]
                image.save(output, format="JPEG", quality=quality, optimize=True)
            elif format.lower() == "png":
                compress_level = quality or self.quality_settings["png"]
                image.save(output, format="PNG", optimize=True, compress_level=compress_level)
            else:
                # Default to original format
                image.save(output, format=image.format or "JPEG")
            
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Image optimization failed: {e}")
            return image_data  # Return original if optimization fails
    
    async def cache_image(self, image_path: str, image_data: bytes,
                         width: Optional[int] = None, height: Optional[int] = None,
                         format: str = "webp") -> str:
        """Cache optimized image"""
        cache_key = self.get_cache_key(image_path, width, height, format)
        cached_path = self.get_cached_path(cache_key, format)
        
        try:
            # Optimize image
            optimized_data = await self.optimize_image(
                image_data, width, height, format
            )
            
            # Save to cache
            async with aiofiles.open(cached_path, 'wb') as f:
                await f.write(optimized_data)
            
            # Cache in Redis if available
            if REDIS_AVAILABLE and cache:
                redis_key = f"image_cache:{cache_key}"
                await cache.set_binary(redis_key, optimized_data, ttl=self.cache_ttl)
            
            logger.info(f"Cached image: {cache_key} ({len(optimized_data)} bytes)")
            return str(cached_path)
            
        except Exception as e:
            logger.error(f"Image caching failed: {e}")
            return ""
    
    async def get_cached_image(self, image_path: str, width: Optional[int] = None,
                              height: Optional[int] = None, format: str = "webp") -> Optional[bytes]:
        """Get cached image data"""
        cache_key = self.get_cache_key(image_path, width, height, format)
        
        # Try Redis cache first
        if REDIS_AVAILABLE and cache:
            redis_key = f"image_cache:{cache_key}"
            cached_data = await cache.get_binary(redis_key)
            if cached_data:
                return cached_data
        
        # Try file cache
        cached_path = self.get_cached_path(cache_key, format)
        if cached_path.exists():
            try:
                async with aiofiles.open(cached_path, 'rb') as f:
                    return await f.read()
            except Exception as e:
                logger.error(f"Failed to read cached image: {e}")
        
        return None
    
    async def generate_responsive_images(self, image_path: str, image_data: bytes) -> Dict[str, str]:
        """Generate responsive image variants"""
        variants = {}
        
        for size in self.responsive_sizes:
            for format in ["webp", "jpeg"]:
                cached_path = await self.cache_image(
                    image_path, image_data, width=size, format=format
                )
                if cached_path:
                    variants[f"{size}w_{format}"] = cached_path
        
        return variants
    
    async def cleanup_cache(self):
        """Clean up old cached files"""
        try:
            current_size = 0
            files_by_age = []
            
            # Calculate current cache size and collect file info
            for file_path in self.cache_dir.rglob("*"):
                if file_path.is_file():
                    stat = file_path.stat()
                    current_size += stat.st_size
                    files_by_age.append((stat.st_mtime, stat.st_size, file_path))
            
            # If cache is too large, remove oldest files
            if current_size > self.max_cache_size:
                files_by_age.sort()  # Sort by modification time
                
                while current_size > self.max_cache_size * 0.8:  # Clean to 80%
                    if not files_by_age:
                        break
                    
                    _, file_size, file_path = files_by_age.pop(0)
                    try:
                        file_path.unlink()
                        current_size -= file_size
                        logger.info(f"Removed cached file: {file_path}")
                    except Exception as e:
                        logger.error(f"Failed to remove cached file {file_path}: {e}")
            
            logger.info(f"Cache cleanup completed. Current size: {current_size / 1024 / 1024:.2f}MB")
            
        except Exception as e:
            logger.error(f"Cache cleanup failed: {e}")

class StaticFileOptimizationMiddleware(BaseHTTPMiddleware):
    """Middleware for optimizing static file serving"""
    
    def __init__(self, app, cache_manager: ImageCacheManager):
        super().__init__(app)
        self.cache_manager = cache_manager
        
        # File extensions that should be cached
        self.cacheable_extensions = {
            '.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg',
            '.css', '.js', '.woff', '.woff2', '.ttf', '.eot'
        }
        
        # Cache control headers
        self.cache_headers = {
            'images': {'Cache-Control': 'public, max-age=86400'},  # 1 day
            'fonts': {'Cache-Control': 'public, max-age=31536000'},  # 1 year
            'css': {'Cache-Control': 'public, max-age=86400'},  # 1 day
            'js': {'Cache-Control': 'public, max-age=86400'},  # 1 day
        }
    
    async def dispatch(self, request: Request, call_next):
        """Process static file requests with optimization"""
        response = await call_next(request)
        
        # Only process GET requests for static files
        if request.method != "GET":
            return response
        
        path = request.url.path
        
        # Check if this is a static file request
        if not any(path.endswith(ext) for ext in self.cacheable_extensions):
            return response
        
        # Add appropriate cache headers
        file_ext = Path(path).suffix.lower()
        
        if file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']:
            response.headers.update(self.cache_headers['images'])
        elif file_ext in ['.woff', '.woff2', '.ttf', '.eot']:
            response.headers.update(self.cache_headers['fonts'])
        elif file_ext == '.css':
            response.headers.update(self.cache_headers['css'])
        elif file_ext == '.js':
            response.headers.update(self.cache_headers['js'])
        
        # Add compression headers
        response.headers['Vary'] = 'Accept-Encoding'
        
        return response

class ImageServingRouter:
    """Router for optimized image serving"""
    
    def __init__(self, cache_manager: ImageCacheManager):
        self.cache_manager = cache_manager
    
    async def serve_optimized_image(self, image_path: str, width: Optional[int] = None,
                                   height: Optional[int] = None, format: Optional[str] = None,
                                   request: Request = None) -> Response:
        """Serve optimized image with caching"""
        
        # Determine best format based on client support
        if not format:
            accept_header = request.headers.get("accept", "") if request else ""
            if "image/webp" in accept_header:
                format = "webp"
            else:
                format = "jpeg"
        
        # Try to get cached image
        cached_data = await self.cache_manager.get_cached_image(
            image_path, width, height, format
        )
        
        if cached_data:
            # Serve from cache
            content_type = f"image/{format}"
            return Response(
                content=cached_data,
                media_type=content_type,
                headers={
                    "Cache-Control": "public, max-age=86400",
                    "ETag": hashlib.md5(cached_data).hexdigest()[:16]
                }
            )
        
        # Load original image and cache optimized version
        try:
            # This would typically load from your storage system
            # For now, returning a 404 if not cached
            raise HTTPException(status_code=404, detail="Image not found")
            
        except Exception as e:
            logger.error(f"Failed to serve image {image_path}: {e}")
            raise HTTPException(status_code=500, detail="Image serving failed")

def setup_static_files(app: FastAPI, static_dir: str = "static"):
    """Setup static file serving with optimization"""
    
    # Create static directory if it doesn't exist
    static_path = Path(static_dir)
    static_path.mkdir(exist_ok=True)
    
    # Create subdirectories
    (static_path / "images").mkdir(exist_ok=True)
    (static_path / "css").mkdir(exist_ok=True)
    (static_path / "js").mkdir(exist_ok=True)
    (static_path / "fonts").mkdir(exist_ok=True)
    
    # Mount static files with caching
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    
    # Initialize image cache manager
    cache_manager = ImageCacheManager(cache_dir=f"{static_dir}/cache")
    
    # Add optimization middleware
    app.add_middleware(StaticFileOptimizationMiddleware, cache_manager=cache_manager)
    
    logger.info(f"✅ Static file serving configured with caching: {static_dir}")
    
    return cache_manager

def get_image_cache_stats(cache_manager: ImageCacheManager) -> Dict[str, Any]:
    """Get image cache statistics"""
    try:
        cache_dir = cache_manager.cache_dir
        total_files = 0
        total_size = 0
        
        if cache_dir.exists():
            for file_path in cache_dir.rglob("*"):
                if file_path.is_file():
                    total_files += 1
                    total_size += file_path.stat().st_size
        
        return {
            "cache_directory": str(cache_dir),
            "total_cached_files": total_files,
            "total_cache_size_mb": round(total_size / 1024 / 1024, 2),
            "max_cache_size_mb": round(cache_manager.max_cache_size / 1024 / 1024, 2),
            "cache_usage_percent": round((total_size / cache_manager.max_cache_size) * 100, 2),
            "supported_formats": ["webp", "jpeg", "png"],
            "responsive_sizes": cache_manager.responsive_sizes
        }
        
    except Exception as e:
        return {"error": str(e)}

# Global cache manager instance
image_cache_manager = None

def get_image_cache_manager() -> Optional[ImageCacheManager]:
    """Get global image cache manager"""
    # Import here to avoid circular imports
    try:
        from ..main import image_cache_manager as global_manager
        return global_manager
    except ImportError:
        return image_cache_manager

# Export utilities
__all__ = [
    'ImageCacheManager', 'StaticFileOptimizationMiddleware', 
    'ImageServingRouter', 'setup_static_files', 'get_image_cache_stats',
    'get_image_cache_manager'
]
