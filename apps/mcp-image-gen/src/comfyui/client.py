import httpx
import json
import uuid
import asyncio
import tempfile
import subprocess
import os
import websockets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "shared" / "python"))
from config import config


class ComfyUIClient:
    def __init__(self):
        self.base_url = config.COMFYUI_URL
        self.client_id = str(uuid.uuid4())
        # SD 1.5 checkpoint for AnimateDiff (AnimateDiff requires SD 1.5, not SDXL)
        self.sd15_checkpoint = "realisticVisionV60B1_v51VAE.safetensors"
        # AnimateDiff motion model
        self.motion_model = "mm_sd_v15_v2.ckpt"
    
    def _get_image_workflow(self, prompt: str, width: int, height: int, seed: int = None) -> dict:
        """Legacy workflow for generating a single static image (SDXL)."""
        if seed is None:
            seed = int(uuid.uuid4().int % (2**32))
        
        workflow = {
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "cfg": 7,
                    "denoise": 1,
                    "latent_image": ["5", 0],
                    "model": ["4", 0],
                    "negative": ["7", 0],
                    "positive": ["6", 0],
                    "sampler_name": "euler_ancestral",
                    "scheduler": "normal",
                    "seed": seed,
                    "steps": 25
                }
            },
            "4": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {
                    "ckpt_name": "sd_xl_base_1.0.safetensors"
                }
            },
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "batch_size": 1,
                    "height": height,
                    "width": width
                }
            },
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": ["4", 1],
                    "text": prompt
                }
            },
            "7": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": ["4", 1],
                    "text": "blurry, low quality, distorted, deformed, ugly, bad anatomy"
                }
            },
            "8": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["3", 0],
                    "vae": ["4", 2]
                }
            },
            "9": {
                "class_type": "SaveImage",
                "inputs": {
                    "filename_prefix": "video_frame",
                    "images": ["8", 0]
                }
            }
        }
        return workflow
    
    def _get_animatediff_workflow(
        self,
        prompt: str,
        width: int,
        height: int,
        num_frames: int = 16,
        seed: int = None,
        fps: int = 8
    ) -> dict:
        """AnimateDiff workflow using Gen2 Evolved Sampling.
        
        Outputs frames via SaveImage. We combine them into MP4 ourselves
        using ffmpeg (more reliable than the deprecated ADE_AnimateDiffCombine).
        
        Node pipeline:
        - Node 10: CheckpointLoaderSimple (SD 1.5) -> MODEL, CLIP, VAE
        - Node 11: ADE_LoadAnimateDiffModel -> MOTION_MODEL_ADE
        - Node 12: ADE_ApplyAnimateDiffModelSimple (motion_model) -> M_MODELS
        - Node 13: ADE_UseEvolvedSampling (model + m_models) -> MODEL (with motion)
        - Node 14: EmptyLatentImage (batch_size = num_frames)
        - Node 15: CLIPTextEncode (positive prompt)
        - Node 16: CLIPTextEncode (negative prompt)
        - Node 17: KSampler (using evolved model)
        - Node 18: VAEDecode
        - Node 19: SaveImage (save all frames for ffmpeg combining)
        """
        if seed is None:
            seed = int(uuid.uuid4().int % (2**32))
        
        # Use a unique prefix so we can find our frames
        filename_prefix = f"animatediff_{uuid.uuid4().hex[:8]}"
        
        workflow = {
            # Load SD 1.5 checkpoint -> MODEL, CLIP, VAE
            "10": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {
                    "ckpt_name": self.sd15_checkpoint
                }
            },
            # Load AnimateDiff motion model -> MOTION_MODEL_ADE
            "11": {
                "class_type": "ADE_LoadAnimateDiffModel",
                "inputs": {
                    "model_name": self.motion_model
                }
            },
            # Apply motion model -> M_MODELS
            "12": {
                "class_type": "ADE_ApplyAnimateDiffModelSimple",
                "inputs": {
                    "motion_model": ["11", 0]
                }
            },
            # Use Evolved Sampling: inject motion models into SD model -> MODEL
            "13": {
                "class_type": "ADE_UseEvolvedSampling",
                "inputs": {
                    "model": ["10", 0],
                    "beta_schedule": "autoselect",
                    "m_models": ["12", 0]
                }
            },
            # Empty latent image with batch_size = num_frames for animation
            "14": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "batch_size": num_frames,
                    "height": height,
                    "width": width
                }
            },
            # Positive prompt
            "15": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": ["10", 1],
                    "text": prompt
                }
            },
            # Negative prompt
            "16": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": ["10", 1],
                    "text": "blurry, low quality, distorted, deformed, ugly, bad anatomy, watermark, text, static, still, no motion, frozen"
                }
            },
            # KSampler using the evolved (motion-injected) model
            "17": {
                "class_type": "KSampler",
                "inputs": {
                    "cfg": 7.5,
                    "denoise": 1,
                    "latent_image": ["14", 0],
                    "model": ["13", 0],
                    "negative": ["16", 0],
                    "positive": ["15", 0],
                    "sampler_name": "euler_ancestral",
                    "scheduler": "normal",
                    "seed": seed,
                    "steps": 20
                }
            },
            # VAE Decode -> images batch
            "18": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["17", 0],
                    "vae": ["10", 2]
                }
            },
            # SaveImage: saves all frames (batch) as individual PNGs
            "19": {
                "class_type": "SaveImage",
                "inputs": {
                    "filename_prefix": filename_prefix,
                    "images": ["18", 0]
                }
            }
        }
        return workflow, filename_prefix
    
    async def generate_image(self, prompt: str, width: int = 1024, height: int = 576, seed: int = None) -> bytes:
        """Generate a single static image using SDXL. (Legacy method)"""
        workflow = self._get_image_workflow(prompt, width, height, seed)
        
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{self.base_url}/prompt",
                json={"prompt": workflow, "client_id": self.client_id}
            )
            response.raise_for_status()
            prompt_id = response.json()["prompt_id"]
        
        ws_url = self.base_url.replace("http", "ws") + f"/ws?clientId={self.client_id}"
        
        async with websockets.connect(ws_url) as ws:
            while True:
                message = await ws.recv()
                if isinstance(message, str):
                    data = json.loads(message)
                    if data.get("type") == "executing":
                        if data["data"].get("node") is None and data["data"].get("prompt_id") == prompt_id:
                            break
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(f"{self.base_url}/history/{prompt_id}")
            response.raise_for_status()
            history = response.json()
            
            outputs = history[prompt_id]["outputs"]
            image_data = None
            
            for node_id, node_output in outputs.items():
                if "images" in node_output:
                    image_info = node_output["images"][0]
                    filename = image_info["filename"]
                    subfolder = image_info.get("subfolder", "")
                    
                    params = {"filename": filename, "type": "output"}
                    if subfolder:
                        params["subfolder"] = subfolder
                    
                    img_response = await client.get(f"{self.base_url}/view", params=params)
                    img_response.raise_for_status()
                    image_data = img_response.content
                    break
            
            return image_data
    
    async def _download_frames_and_combine(
        self, client: httpx.AsyncClient, image_infos: list, fps: int
    ) -> bytes:
        """Download individual frames from ComfyUI and combine into MP4 using ffmpeg."""
        temp_dir = tempfile.mkdtemp(prefix="animatediff_")
        
        try:
            # Download all frames
            for i, img_info in enumerate(image_infos):
                params = {
                    "filename": img_info["filename"],
                    "type": img_info.get("type", "output")
                }
                if img_info.get("subfolder"):
                    params["subfolder"] = img_info["subfolder"]
                
                resp = await client.get(f"{self.base_url}/view", params=params)
                resp.raise_for_status()
                
                frame_path = os.path.join(temp_dir, f"frame_{i:05d}.png")
                with open(frame_path, "wb") as f:
                    f.write(resp.content)
            
            # Combine frames into MP4 using ffmpeg
            output_path = os.path.join(temp_dir, "output.mp4")
            
            cmd = [
                "ffmpeg", "-y",
                "-framerate", str(fps),
                "-i", os.path.join(temp_dir, "frame_%05d.png"),
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-preset", "medium",
                "-crf", "23",
                output_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                raise Exception(f"ffmpeg failed: {result.stderr[:500]}")
            
            with open(output_path, "rb") as f:
                video_data = f.read()
            
            return video_data
            
        finally:
            # Cleanup temp files
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    async def generate_video_clip(
        self,
        prompt: str,
        width: int = 512,
        height: int = 512,
        num_frames: int = 16,
        fps: int = 8,
        seed: int = None
    ) -> bytes:
        """Generate an animated video clip using AnimateDiff.
        
        Returns the raw bytes of the generated MP4 video clip.
        AnimateDiff works best at 512x512 resolution with SD 1.5.
        Default 16 frames at 8fps = 2 seconds of animation.
        
        Workflow: AnimateDiff generates frames via SaveImage, then
        we download them and combine into MP4 using ffmpeg.
        """
        workflow, filename_prefix = self._get_animatediff_workflow(
            prompt=prompt,
            width=width,
            height=height,
            num_frames=num_frames,
            seed=seed,
            fps=fps
        )
        
        # Submit the workflow
        async with httpx.AsyncClient(timeout=600.0) as client:
            response = await client.post(
                f"{self.base_url}/prompt",
                json={"prompt": workflow, "client_id": self.client_id}
            )
            response.raise_for_status()
            result = response.json()
            
            prompt_id = result["prompt_id"]
            
            # Check if there were node errors in the prompt submission
            if result.get("node_errors"):
                error_details = json.dumps(result["node_errors"], indent=2)[:500]
                raise Exception(f"ComfyUI workflow errors: {error_details}")
        
        # Wait for completion via websocket
        ws_url = self.base_url.replace("http", "ws") + f"/ws?clientId={self.client_id}"
        
        async with websockets.connect(ws_url, ping_interval=30, ping_timeout=120) as ws:
            while True:
                message = await ws.recv()
                if isinstance(message, str):
                    data = json.loads(message)
                    msg_type = data.get("type")
                    
                    if msg_type == "execution_error":
                        err_data = data.get("data", {})
                        raise Exception(
                            f"ComfyUI execution error on node {err_data.get('node_type', 'unknown')}: "
                            f"{err_data.get('exception_message', 'Unknown error')}"
                        )
                    
                    if msg_type == "executing":
                        if data["data"].get("node") is None and data["data"].get("prompt_id") == prompt_id:
                            break
        
        # Retrieve frames and combine into video
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.get(f"{self.base_url}/history/{prompt_id}")
            response.raise_for_status()
            history = response.json()
            
            outputs = history[prompt_id]["outputs"]
            
            # Find the SaveImage output (node 19) with our frames
            image_infos = []
            for node_id, node_output in outputs.items():
                if "images" in node_output:
                    for img_info in node_output["images"]:
                        # Match our filename prefix
                        if img_info["filename"].startswith(filename_prefix):
                            image_infos.append(img_info)
            
            if not image_infos:
                # Fallback: take all images from any node
                for node_id, node_output in outputs.items():
                    if "images" in node_output:
                        image_infos.extend(node_output["images"])
            
            if not image_infos:
                raise Exception("No frames generated by AnimateDiff workflow")
            
            # Sort frames by filename to ensure correct order
            image_infos.sort(key=lambda x: x["filename"])
            
            # Download frames and combine into MP4
            video_data = await self._download_frames_and_combine(
                client, image_infos, fps
            )
            
            return video_data
    
    async def check_health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/system_stats")
                return response.status_code == 200
        except:
            return False


comfyui_client = ComfyUIClient()
