try:
    import pyautogui
except ImportError:
    pyautogui = None

import base64
import io
import logging

logger = logging.getLogger("jarvis.vision")

class DesktopVision:
    @staticmethod
    def capture_screen_base64() -> str:
        """ Captures full screen and returns JPEG Base64 encoding. """
        print("[VISION] Capturing full screen...")
        if not pyautogui:
            print("[VISION] (Simulated Capture) Returning mock desktop screenshot.")
            # Simple mock JPEG Base64
            return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
            
        try:
            screenshot = pyautogui.screenshot()
            buffer = io.BytesIO()
            screenshot.convert('RGB').save(buffer, format="JPEG", quality=75)
            encoded = base64.b64encode(buffer.getvalue()).decode('utf-8')
            return encoded
        except Exception as e:
            logger.error(f"Failed to capture full screen: {e}")
            return ""

            
    @staticmethod
    def capture_crop_base64(x: int, y: int, w: int, h: int) -> str:
        """ Captures a specific crop bounding box on the screen. """
        print(f"[VISION] Capturing crop bounding box: x={x}, y={y}, w={w}, h={h}")
        if not pyautogui:
            print("[VISION] (Simulated Crop Capture) Returning mock desktop screen crop.")
            return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
            
        try:
            screenshot = pyautogui.screenshot(region=(x, y, w, h))
            buffer = io.BytesIO()
            screenshot.convert('RGB').save(buffer, format="JPEG", quality=85)
            encoded = base64.b64encode(buffer.getvalue()).decode('utf-8')
            return encoded
        except Exception as e:
            logger.error(f"Failed to capture crop: {e}")
            return ""
            
    @staticmethod
    def describe_screen_layout(image_base64: str = None) -> str:
        """ Uses Groq LLaMA 3.2 Vision Model to analyze the screen layout and perform visual OCR. """
        b64_data = image_base64 or DesktopVision.capture_screen_base64()
        if not b64_data:
            return "ERROR: Unable to capture screen frame for analysis."
            
        try:
            from MODELS.CLOUD.groq_client import GroqClient
            client = GroqClient()
            prompt = (
                "You are the visual cortex of JARVIS.\n"
                "Analyze this desktop screenshot and perform highly accurate visual OCR. "
                "Identify which apps are open, active windows, buttons, and summarize visible text."
            )
            print("[VISION MODEL] Sending screen frame to LLaMA 3.2 Vision on Groq Acceleration Grid...")
            description = client.generate(prompt, "llama-3.2-11b-vision-preview", image_base64=b64_data)
            return description
        except Exception as e:
            logger.error(f"Screen layout description failed: {e}")
            return f"ERROR: Visual cortex parsing failure: {str(e)}"

    @staticmethod
    def omni_parse(goal: str = None) -> dict:
        """
        OmniParser visual grounding:
        Parses desktop into Set-of-Marks UI elements and locates target.
        """
        from VISION.omni_parser import omni_parser
        img = omni_parser.capture_screen()
        elements = omni_parser.parse_ui_elements(img)
        som_img, som_b64, registry = omni_parser.generate_som_image(img, elements)
        
        result = {
            "total_elements": len(elements),
            "elements": [e.to_dict() for e in elements],
            "som_image_b64": som_b64
        }
        
        if goal:
            plan = omni_parser.target_action(goal, elements, som_b64)
            result["action_plan"] = plan
            
        return result

    @staticmethod
    def visual_click(directive: str) -> dict:
        """
        Execute pixel-grounded mouse click on UI element matching directive.
        """
        from VISION.omni_parser import omni_parser
        return omni_parser.visual_action(directive)

