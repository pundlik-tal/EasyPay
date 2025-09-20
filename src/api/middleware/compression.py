"""
EasyPay Payment Gateway - Response Compression Middleware

This module provides response compression middleware for improved performance
and reduced bandwidth usage.
"""

import gzip
import brotli
import time
import logging
from typing import Callable, Optional, Dict, Any
from io import BytesIO

from fastapi import Request, Response
from fastapi.responses import StreamingResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.infrastructure.monitoring import RESPONSE_SIZE


class CompressionMiddleware(BaseHTTPMiddleware):
    """Middleware for compressing HTTP responses."""
    
    def __init__(
        self,
        app: ASGIApp,
        minimum_size: int = 1024,
        compression_level: int = 6,
        supported_encodings: list = None
    ):
        super().__init__(app)
        self.minimum_size = minimum_size
        self.compression_level = compression_level
        self.supported_encodings = supported_encodings or ["gzip", "br"]
        self.logger = logging.getLogger(__name__)
        
        # Content types that should be compressed
        self.compressible_types = {
            "application/json",
            "application/javascript",
            "application/xml",
            "text/css",
            "text/csv",
            "text/html",
            "text/javascript",
            "text/plain",
            "text/xml",
            "application/vnd.api+json"
        }
        
        # Content types that should not be compressed
        self.non_compressible_types = {
            "image/jpeg",
            "image/png",
            "image/gif",
            "image/webp",
            "image/svg+xml",
            "video/mp4",
            "video/webm",
            "audio/mpeg",
            "audio/wav",
            "application/pdf",
            "application/zip",
            "application/gzip"
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and compress response if appropriate."""
        
        start_time = time.time()
        
        # Check if client accepts compression
        accept_encoding = request.headers.get("accept-encoding", "")
        client_supports_gzip = "gzip" in accept_encoding
        client_supports_brotli = "br" in accept_encoding
        
        if not (client_supports_gzip or client_supports_brotli):
            # Client doesn't support compression
            response = await call_next(request)
            return response
        
        # Process the request
        response = await call_next(request)
        
        # Check if response should be compressed
        if not self._should_compress(response):
            return response
        
        # Get response body
        response_body = await self._get_response_body(response)
        
        if len(response_body) < self.minimum_size:
            # Response is too small to benefit from compression
            return response
        
        # Choose compression method
        compression_method = self._choose_compression_method(
            client_supports_gzip,
            client_supports_brotli
        )
        
        if not compression_method:
            return response
        
        # Compress the response
        compressed_body, compression_ratio = await self._compress_response(
            response_body,
            compression_method
        )
        
        # Only use compression if it provides significant benefit
        if compression_ratio < 0.1:  # Less than 10% compression
            return response
        
        # Create compressed response
        compressed_response = self._create_compressed_response(
            response,
            compressed_body,
            compression_method
        )
        
        # Log compression metrics
        processing_time = time.time() - start_time
        self._log_compression_metrics(
            response,
            len(response_body),
            len(compressed_body),
            compression_ratio,
            processing_time
        )
        
        return compressed_response
    
    def _should_compress(self, response: Response) -> bool:
        """Check if response should be compressed."""
        
        # Don't compress if already compressed
        if "content-encoding" in response.headers:
            return False
        
        # Check content type
        content_type = response.headers.get("content-type", "").split(";")[0].strip()
        
        if content_type in self.non_compressible_types:
            return False
        
        if content_type in self.compressible_types:
            return True
        
        # Default to compressing text-based content
        return content_type.startswith("text/") or content_type.startswith("application/")
    
    def _choose_compression_method(
        self,
        supports_gzip: bool,
        supports_brotli: bool
    ) -> Optional[str]:
        """Choose the best compression method based on client support."""
        
        # Prefer Brotli if supported (better compression)
        if supports_brotli and "br" in self.supported_encodings:
            return "br"
        
        # Fall back to gzip
        if supports_gzip and "gzip" in self.supported_encodings:
            return "gzip"
        
        return None
    
    async def _get_response_body(self, response: Response) -> bytes:
        """Get response body as bytes."""
        
        if hasattr(response, "body"):
            return response.body
        
        # For streaming responses, we need to collect the body
        body_parts = []
        async for chunk in response.body_iterator:
            body_parts.append(chunk)
        
        return b"".join(body_parts)
    
    async def _compress_response(
        self,
        body: bytes,
        method: str
    ) -> tuple[bytes, float]:
        """Compress response body and return compressed data and ratio."""
        
        try:
            if method == "gzip":
                compressed = gzip.compress(body, compresslevel=self.compression_level)
            elif method == "br":
                compressed = brotli.compress(body, quality=self.compression_level)
            else:
                raise ValueError(f"Unsupported compression method: {method}")
            
            compression_ratio = 1 - (len(compressed) / len(body))
            
            return compressed, compression_ratio
            
        except Exception as e:
            self.logger.error(f"Compression failed: {e}")
            return body, 0.0
    
    def _create_compressed_response(
        self,
        original_response: Response,
        compressed_body: bytes,
        method: str
    ) -> Response:
        """Create a new response with compressed body."""
        
        # Create new response with compressed body
        response = Response(
            content=compressed_body,
            status_code=original_response.status_code,
            headers=dict(original_response.headers),
            media_type=original_response.media_type
        )
        
        # Add compression headers
        response.headers["content-encoding"] = method
        response.headers["content-length"] = str(len(compressed_body))
        
        # Add Vary header to indicate compression varies
        vary_header = response.headers.get("vary", "")
        if vary_header:
            vary_header += ", Accept-Encoding"
        else:
            vary_header = "Accept-Encoding"
        response.headers["vary"] = vary_header
        
        return response
    
    def _log_compression_metrics(
        self,
        response: Response,
        original_size: int,
        compressed_size: int,
        compression_ratio: float,
        processing_time: float
    ):
        """Log compression metrics."""
        
        # Update Prometheus metrics
        RESPONSE_SIZE.labels(
            method="COMPRESSED",
            endpoint="compression_middleware"
        ).observe(compressed_size)
        
        # Log detailed metrics
        self.logger.info(
            f"Response compressed: {original_size} -> {compressed_size} bytes "
            f"({compression_ratio:.1%} reduction) in {processing_time:.3f}s"
        )


class SelectiveCompressionMiddleware(CompressionMiddleware):
    """Middleware that selectively compresses responses based on content and size."""
    
    def __init__(
        self,
        app: ASGIApp,
        minimum_size: int = 1024,
        compression_level: int = 6,
        supported_encodings: list = None,
        compression_threshold: float = 0.1
    ):
        super().__init__(app, minimum_size, compression_level, supported_encodings)
        self.compression_threshold = compression_threshold
    
    def _should_compress(self, response: Response) -> bool:
        """Enhanced compression decision logic."""
        
        # Check basic compression criteria
        if not super()._should_compress(response):
            return False
        
        # Check response size
        content_length = response.headers.get("content-length")
        if content_length and int(content_length) < self.minimum_size:
            return False
        
        # Check for specific headers that indicate compression should be avoided
        cache_control = response.headers.get("cache-control", "")
        if "no-transform" in cache_control:
            return False
        
        return True
    
    async def _compress_response(
        self,
        body: bytes,
        method: str
    ) -> tuple[bytes, float]:
        """Enhanced compression with threshold checking."""
        
        compressed, compression_ratio = await super()._compress_response(body, method)
        
        # Only return compressed data if it meets the threshold
        if compression_ratio < self.compression_threshold:
            return body, 0.0
        
        return compressed, compression_ratio


class AdaptiveCompressionMiddleware(CompressionMiddleware):
    """Middleware that adapts compression based on server load and response patterns."""
    
    def __init__(
        self,
        app: ASGIApp,
        minimum_size: int = 1024,
        compression_level: int = 6,
        supported_encodings: list = None,
        adaptive_threshold: float = 0.7
    ):
        super().__init__(app, minimum_size, compression_level, supported_encodings)
        self.adaptive_threshold = adaptive_threshold
        self.compression_stats = {
            'total_requests': 0,
            'compressed_requests': 0,
            'total_original_size': 0,
            'total_compressed_size': 0
        }
    
    def _should_compress(self, response: Response) -> bool:
        """Adaptive compression decision based on historical data."""
        
        # Check basic criteria first
        if not super()._should_compress(response):
            return False
        
        # Calculate current compression ratio
        if self.compression_stats['total_original_size'] > 0:
            current_ratio = (
                self.compression_stats['total_compressed_size'] /
                self.compression_stats['total_original_size']
            )
            
            # If compression is not effective, reduce compression
            if current_ratio > self.adaptive_threshold:
                return False
        
        return True
    
    def _log_compression_metrics(
        self,
        response: Response,
        original_size: int,
        compressed_size: int,
        compression_ratio: float,
        processing_time: float
    ):
        """Update adaptive compression statistics."""
        
        # Update stats
        self.compression_stats['total_requests'] += 1
        self.compression_stats['compressed_requests'] += 1
        self.compression_stats['total_original_size'] += original_size
        self.compression_stats['total_compressed_size'] += compressed_size
        
        # Call parent logging
        super()._log_compression_metrics(
            response, original_size, compressed_size, compression_ratio, processing_time
        )
    
    def get_compression_stats(self) -> Dict[str, Any]:
        """Get current compression statistics."""
        
        stats = self.compression_stats.copy()
        
        if stats['total_requests'] > 0:
            stats['compression_rate'] = stats['compressed_requests'] / stats['total_requests']
        else:
            stats['compression_rate'] = 0
        
        if stats['total_original_size'] > 0:
            stats['overall_compression_ratio'] = (
                1 - stats['total_compressed_size'] / stats['total_original_size']
            )
        else:
            stats['overall_compression_ratio'] = 0
        
        return stats


def create_compression_middleware(
    app: ASGIApp,
    compression_type: str = "standard",
    **kwargs
) -> BaseHTTPMiddleware:
    """Factory function to create compression middleware."""
    
    if compression_type == "selective":
        return SelectiveCompressionMiddleware(app, **kwargs)
    elif compression_type == "adaptive":
        return AdaptiveCompressionMiddleware(app, **kwargs)
    else:
        return CompressionMiddleware(app, **kwargs)
