"""
Keyword extraction module for storyboard frames.
Supports multiple backends: OpenAI Vision API, local BLIP model, or basic image analysis.
"""
import os
import base64
from typing import Optional, List, Dict, Any
from pathlib import Path

from app.config import settings


class KeywordExtractor:
    """Extract keywords from images using various backends."""
    
    def __init__(self, backend: Optional[str] = None):
        """
        Initialize keyword extractor.
        
        Args:
            backend: "openai", "blip", "basic", or "auto" (tries openai -> blip -> basic)
                    If None, uses KEYWORD_EXTRACTION_BACKEND from settings
        """
        self.backend = backend or settings.keyword_extraction_backend
        self.openai_client = None
        self.openai_model = settings.openai_model
        self.blip_model = None
        self.blip_processor = None
        self.max_keywords = settings.keyword_max_count
        
        if self.backend == "auto":
            self._initialize_auto()
        elif self.backend == "openai":
            self._initialize_openai()
        elif self.backend == "blip":
            self._initialize_blip()
        elif self.backend == "basic":
            self._initialize_basic()
    
    def _initialize_auto(self):
        """Auto-detect and initialize the best available backend."""
        # Try OpenAI first if API key is available
        api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY")
        if api_key:
            try:
                self._initialize_openai()
                self.backend = "openai"
                return
            except Exception:
                pass
        
        # Try BLIP model
        try:
            self._initialize_blip()
            self.backend = "blip"
            return
        except Exception:
            pass
        
        # Fallback to basic
        self._initialize_basic()
        self.backend = "basic"
    
    def _initialize_openai(self):
        """Initialize OpenAI Vision API client."""
        try:
            import openai
            api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not set in environment or settings")
            
            # Get base URL from settings or environment (for custom endpoints)
            base_url = settings.openai_base_url or os.getenv("OPENAI_BASE_URL")
            
            # Initialize client with optional custom base URL
            client_kwargs = {"api_key": api_key}
            if base_url:
                client_kwargs["base_url"] = base_url
            
            self.openai_client = openai.OpenAI(**client_kwargs)
        except ImportError:
            raise ImportError("openai package not installed. Install with: pip install openai")
        except Exception as e:
            raise Exception(f"Failed to initialize OpenAI client: {e}")
    
    def _initialize_blip(self):
        """Initialize BLIP model for local image captioning."""
        try:
            from transformers import BlipProcessor, BlipForConditionalGeneration
            import torch
            
            # Use CPU by default, can be changed to CUDA if available
            device = "cuda" if torch.cuda.is_available() else "cpu"
            
            print("Loading BLIP model for keyword extraction...")
            self.blip_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
            self.blip_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
            self.blip_model.to(device)
            self.blip_model.eval()
            self.blip_device = device
            print("BLIP model loaded successfully")
        except ImportError:
            raise ImportError("transformers and torch packages not installed. Install with: pip install transformers torch")
        except Exception as e:
            raise Exception(f"Failed to initialize BLIP model: {e}")
    
    def _initialize_basic(self):
        """Initialize basic keyword extraction (placeholder for future implementation)."""
        # This could use basic image analysis, color detection, etc.
        pass
    
    def _encode_image_to_base64(self, image_path: str) -> str:
        """Encode image file to base64 string."""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    async def extract_keywords_openai(self, image_path: str, max_keywords: Optional[int] = None) -> List[str]:
        """Extract keywords using OpenAI Vision API."""
        if not self.openai_client:
            raise ValueError("OpenAI client not initialized")
        
        max_keywords = max_keywords or self.max_keywords
        
        try:
            # Encode image
            base64_image = self._encode_image_to_base64(image_path)
            
            # Call OpenAI Vision API
            response = self.openai_client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"Analyze this image and extract {max_keywords} keywords that describe the main subjects, objects, actions, and scene. Return only comma-separated keywords, no explanations."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=100
            )
            
            # Parse response
            keywords_text = response.choices[0].message.content.strip()
            keywords = [kw.strip() for kw in keywords_text.split(',') if kw.strip()]
            return keywords[:max_keywords]
        
        except Exception as e:
            print(f"Error extracting keywords with OpenAI: {e}")
            return []
    
    async def extract_keywords_blip(self, image_path: str, max_keywords: Optional[int] = None) -> List[str]:
        """Extract keywords using BLIP model."""
        if not self.blip_model or not self.blip_processor:
            raise ValueError("BLIP model not initialized")
        
        max_keywords = max_keywords or self.max_keywords
        
        try:
            from PIL import Image
            import torch
            
            # Load and process image
            image = Image.open(image_path).convert('RGB')
            inputs = self.blip_processor(image, return_tensors="pt").to(self.blip_device)
            
            # Generate caption
            with torch.no_grad():
                out = self.blip_model.generate(**inputs, max_length=50)
            
            caption = self.blip_processor.decode(out[0], skip_special_tokens=True)
            
            # Extract keywords from caption
            # Simple approach: split caption and filter common words
            stop_words = {'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
                         'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
                         'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these',
                         'those', 'in', 'on', 'at', 'by', 'for', 'with', 'from', 'to', 'of'}
            
            words = caption.lower().replace(',', ' ').replace('.', ' ').split()
            keywords = [w for w in words if w not in stop_words and len(w) > 2]
            
            # Remove duplicates while preserving order
            seen = set()
            unique_keywords = []
            for kw in keywords:
                if kw not in seen:
                    seen.add(kw)
                    unique_keywords.append(kw)
            
            return unique_keywords[:max_keywords]
        
        except Exception as e:
            print(f"Error extracting keywords with BLIP: {e}")
            return []
    
    async def extract_keywords_basic(self, image_path: str, max_keywords: Optional[int] = None) -> List[str]:
        """Extract basic keywords using image analysis."""
        # This is a placeholder - could implement color analysis, edge detection, etc.
        # For now, return empty list
        return []
    
    async def extract_keywords(self, image_path: str, max_keywords: Optional[int] = None) -> List[str]:
        """
        Extract keywords from an image.
        
        Args:
            image_path: Path to image file
            max_keywords: Maximum number of keywords to return (uses default from settings if None)
        
        Returns:
            List of keyword strings
        """
        if not os.path.exists(image_path):
            return []
        
        max_keywords = max_keywords or self.max_keywords
        
        if self.backend == "openai" or (self.backend == "auto" and self.openai_client):
            return await self.extract_keywords_openai(image_path, max_keywords)
        elif self.backend == "blip" or (self.backend == "auto" and self.blip_model):
            return await self.extract_keywords_blip(image_path, max_keywords)
        else:
            return await self.extract_keywords_basic(image_path, max_keywords)
    
    async def extract_keywords_batch(
        self,
        image_paths: List[str],
        max_keywords: Optional[int] = None,
        progress_callback: Optional[Callable] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract keywords from multiple images.
        
        Args:
            image_paths: List of image file paths
            max_keywords: Maximum number of keywords per image (uses default from settings if None)
            progress_callback: Optional callback function(percent, message)
        
        Returns:
            List of dictionaries with 'image_path' and 'keywords' keys
        """
        results = []
        total = len(image_paths)
        max_keywords = max_keywords or self.max_keywords
        
        for idx, image_path in enumerate(image_paths):
            if progress_callback:
                progress = int((idx / total) * 100)
                progress_callback(progress, f"Extracting keywords from image {idx + 1}/{total}...")
            
            keywords = await self.extract_keywords(image_path, max_keywords)
            results.append({
                'image_path': image_path,
                'keywords': keywords
            })
        
        if progress_callback:
            progress_callback(100, "Keyword extraction complete!")
        
        return results

