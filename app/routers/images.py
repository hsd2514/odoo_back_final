"""
Image Serving and Asset Management Router
========================================

Advanced image serving with caching, optimization, and responsive variants.
"""

from fastapi import APIRouter, Depends, Query, Request, Response, HTTPException, Path
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
import asyncio
from pathlib import Path as PathLib
import logging

from ..database import get_db
from ..models.catalog import ProductAsset
from ..utils.image_cache import ImageCacheManager, get_image_cache_manager
from ..utils.auth import require_roles

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/images", tags=["images"])

@router.get(
    "/product/{asset_id}",
    summary="Serve optimized product image",
    description="Serve product image with automatic optimization, caching, and responsive sizing"
)
async def serve_product_image(
    request: Request,
    asset_id: int = Path(..., description="Product asset ID"),
    width: Optional[int] = Query(None, ge=50, le=2000, description="Image width in pixels"),
    height: Optional[int] = Query(None, ge=50, le=2000, description="Image height in pixels"),
    format: Optional[str] = Query(None, regex="^(webp|jpeg|png)$", description="Output format"),
    quality: Optional[int] = Query(None, ge=10, le=100, description="Image quality (10-100)"),
    db: Session = Depends(get_db)
):
    """
    Serve optimized product image with advanced caching and format conversion.
    
    Features:
    - Automatic format detection based on browser support
    - Responsive image sizing
    - WebP conversion for supported browsers
    - Redis and file system caching
    - Compression optimization
    """
    
    # Get product asset from database
    asset = db.query(ProductAsset).filter(ProductAsset.asset_id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Image not found")
    
    cache_manager = get_image_cache_manager()
    if not cache_manager:
        raise HTTPException(status_code=500, detail="Image cache not available")
    
    try:
        # Determine best format based on client support
        if not format:
            accept_header = request.headers.get("accept", "")
            if "image/webp" in accept_header:
                format = "webp"
            else:
                format = "jpeg"
        
        # Generate cache key
        cache_key = cache_manager.get_cache_key(
            f"product_{asset_id}", width, height, format
        )
        
        # Try to get cached image
        cached_data = await cache_manager.get_cached_image(
            f"product_{asset_id}", width, height, format
        )
        
        if cached_data:
            # Serve from cache
            return Response(
                content=cached_data,
                media_type=f"image/{format}",
                headers={
                    "Cache-Control": "public, max-age=86400",
                    "ETag": f'"{cache_key[:16]}"',
                    "X-Cache": "HIT"
                }
            )
        
        # Get original image data
        image_data = None
        
        if asset.data:
            # Image stored inline in database
            image_data = asset.data
        elif asset.uri:
            # Image stored at URI - would need to fetch
            # For demo, we'll simulate this
            raise HTTPException(
                status_code=501, 
                detail="External image fetching not implemented"
            )
        else:
            raise HTTPException(status_code=404, detail="Image data not available")
        
        # Optimize and cache image
        optimized_data = await cache_manager.optimize_image(
            image_data, width, height, format, quality
        )
        
        # Cache the optimized image
        await cache_manager.cache_image(
            f"product_{asset_id}", optimized_data, width, height, format
        )
        
        # Serve optimized image
        return Response(
            content=optimized_data,
            media_type=f"image/{format}",
            headers={
                "Cache-Control": "public, max-age=86400",
                "ETag": f'"{cache_key[:16]}"',
                "X-Cache": "MISS"
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to serve image {asset_id}: {e}")
        raise HTTPException(status_code=500, detail="Image serving failed")

@router.get(
    "/product/{asset_id}/responsive",
    response_model=Dict[str, str],
    summary="Get responsive image variants",
    description="Get URLs for different sizes and formats of a product image"
)
async def get_responsive_variants(
    asset_id: int = Path(..., description="Product asset ID"),
    db: Session = Depends(get_db)
):
    """
    Get responsive image variants for different screen sizes and formats.
    
    Returns URLs for:
    - Multiple widths (150px, 300px, 600px, 900px, 1200px)
    - Multiple formats (WebP, JPEG)
    """
    
    # Verify asset exists
    asset = db.query(ProductAsset).filter(ProductAsset.asset_id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Image not found")
    
    variants = {}
    base_url = f"/images/product/{asset_id}"
    
    # Generate URLs for different sizes and formats
    sizes = [150, 300, 600, 900, 1200]
    formats = ["webp", "jpeg"]
    
    for size in sizes:
        for fmt in formats:
            key = f"{size}w_{fmt}"
            variants[key] = f"{base_url}?width={size}&format={fmt}"
    
    # Add original size variants
    variants["original_webp"] = f"{base_url}?format=webp"
    variants["original_jpeg"] = f"{base_url}?format=jpeg"
    
    return variants

@router.get(
    "/cache/stats",
    response_model=Dict[str, Any],
    summary="Get image cache statistics",
    description="Get detailed statistics about the image cache performance"
)
async def get_cache_stats(_: None = Depends(require_roles("Admin"))):
    """Get image cache statistics and performance metrics."""
    
    from ..utils.image_cache import get_image_cache_stats
    
    cache_manager = get_image_cache_manager()
    if not cache_manager:
        return {"error": "Image cache not available"}
    
    return get_image_cache_stats(cache_manager)

@router.post(
    "/cache/cleanup",
    summary="Clean up image cache",
    description="Remove old cached images to free up space"
)
async def cleanup_cache(_: None = Depends(require_roles("Admin"))):
    """Clean up old cached images."""
    
    cache_manager = get_image_cache_manager()
    if not cache_manager:
        raise HTTPException(status_code=500, detail="Image cache not available")
    
    try:
        await cache_manager.cleanup_cache()
        return {"message": "Cache cleanup completed successfully"}
    except Exception as e:
        logger.error(f"Cache cleanup failed: {e}")
        raise HTTPException(status_code=500, detail="Cache cleanup failed")

@router.post(
    "/cache/warm/{asset_id}",
    summary="Warm cache for product image",
    description="Pre-generate and cache responsive variants for a product image"
)
async def warm_image_cache(
    asset_id: int = Path(..., description="Product asset ID"),
    db: Session = Depends(get_db),
    _: None = Depends(require_roles("Admin"))
):
    """Pre-generate and cache responsive image variants."""
    
    # Get product asset
    asset = db.query(ProductAsset).filter(ProductAsset.asset_id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Image not found")
    
    if not asset.data:
        raise HTTPException(status_code=400, detail="No image data available for caching")
    
    cache_manager = get_image_cache_manager()
    if not cache_manager:
        raise HTTPException(status_code=500, detail="Image cache not available")
    
    try:
        # Generate responsive variants
        variants = await cache_manager.generate_responsive_images(
            f"product_{asset_id}", asset.data
        )
        
        return {
            "message": f"Cache warmed for asset {asset_id}",
            "variants_generated": len(variants),
            "variants": list(variants.keys())
        }
        
    except Exception as e:
        logger.error(f"Cache warming failed for asset {asset_id}: {e}")
        raise HTTPException(status_code=500, detail="Cache warming failed")

@router.get(
    "/formats/supported",
    response_model=Dict[str, Any],
    summary="Get supported image formats",
    description="Get information about supported image formats and their capabilities"
)
async def get_supported_formats():
    """Get information about supported image formats."""
    
    return {
        "input_formats": ["JPEG", "PNG", "WebP", "GIF", "BMP", "TIFF"],
        "output_formats": ["webp", "jpeg", "png"],
        "recommended_format": "webp",
        "fallback_format": "jpeg",
        "features": {
            "webp": {
                "compression": "lossy/lossless",
                "transparency": True,
                "animation": True,
                "size_reduction": "25-35% vs JPEG"
            },
            "jpeg": {
                "compression": "lossy",
                "transparency": False,
                "animation": False,
                "compatibility": "universal"
            },
            "png": {
                "compression": "lossless",
                "transparency": True,
                "animation": False,
                "best_for": "graphics, icons"
            }
        },
        "responsive_sizes": [150, 300, 600, 900, 1200],
        "quality_settings": {
            "webp": "85 (recommended)",
            "jpeg": "85 (recommended)",
            "png": "9 (compression level)"
        }
    }

# Background task endpoints
@router.post(
    "/cache/warm-all",
    summary="Warm cache for all product images",
    description="Background task to pre-generate cache for all product images"
)
async def warm_all_caches(
    limit: int = Query(100, description="Maximum number of images to process"),
    db: Session = Depends(get_db),
    _: None = Depends(require_roles("Admin"))
):
    """Warm cache for all product images (background task)."""
    
    cache_manager = get_image_cache_manager()
    if not cache_manager:
        raise HTTPException(status_code=500, detail="Image cache not available")
    
    # Get assets with inline data
    assets = (
        db.query(ProductAsset)
        .filter(ProductAsset.data.isnot(None))
        .limit(limit)
        .all()
    )
    
    if not assets:
        return {"message": "No assets found for cache warming"}
    
    # Start background warming
    async def warm_assets():
        warmed = 0
        for asset in assets:
            try:
                await cache_manager.generate_responsive_images(
                    f"product_{asset.asset_id}", asset.data
                )
                warmed += 1
                logger.info(f"Warmed cache for asset {asset.asset_id}")
            except Exception as e:
                logger.error(f"Failed to warm cache for asset {asset.asset_id}: {e}")
        
        logger.info(f"Cache warming completed: {warmed}/{len(assets)} assets processed")
    
    # Run in background
    asyncio.create_task(warm_assets())
    
    return {
        "message": "Cache warming started in background",
        "total_assets": len(assets),
        "status": "processing"
    }
