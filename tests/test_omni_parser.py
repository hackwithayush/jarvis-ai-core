"""
Automated Test for JARVIS OmniParser Integration
Verifies screen capture, Set-of-Marks (SoM) visual annotation, UI element detection,
and pixel-grounded action execution.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from VISION.omni_parser import omni_parser
from VISION.desktop_vision import DesktopVision
from core.computer_control import computer_control

def test_omni_parser():
    print("==================================================")
    print("JARVIS OMNIPARSER INTEGRATION VERIFICATION")
    print("==================================================")

    # 1. Capture screen
    print("\n1. Testing screen capture...")
    img = omni_parser.capture_screen()
    assert img is not None, "Screen image must not be None."
    w, h = img.size
    print(f"   [PASS] Captured screen frame: {w}x{h} (mode: {img.mode})")

    # 2. Extract UI elements
    print("\n2. Testing UI element extraction...")
    elements = omni_parser.parse_ui_elements(img)
    assert len(elements) > 0, "Must detect at least 1 UI element."
    print(f"   [PASS] Grounded {len(elements)} interactive UI elements.")
    for el in elements[:4]:
        print(f"      - [{el.id}] {el.element_type.upper()}: '{el.label}' at center {el.center}")

    # 3. Generate Set-of-Marks (SoM) visual annotation
    print("\n3. Testing Set-of-Marks (SoM) rendering...")
    som_img, som_b64, registry = omni_parser.generate_som_image(img, elements)
    assert som_img is not None, "Annotated image must exist."
    assert len(som_b64) > 1000, "Base64 payload must be valid image."
    assert len(registry) == len(elements), "Registry must match element count."
    print(f"   [PASS] Generated Set-of-Marks annotated frame ({len(som_b64)} chars base64).")

    # 4. Target element reasoning
    print("\n4. Testing visual target grounding for 'Click Search'...")
    plan = omni_parser.target_action("Click the search button or search bar", elements, som_b64)
    assert plan.get("status") == "success", f"Target plan should succeed, got {plan}"
    target = plan["target"]
    cx, cy = target["center"]
    print(f"   [PASS] Grounded target: [{target['id']}] '{target['label']}' -> ({cx}, {cy})")
    print(f"          Action: {plan['action']} | Reason: {plan['reason']}")

    # 5. Visual Action End-to-End Execution
    print("\n5. Testing full visual_action loop...")
    res = omni_parser.visual_action("Click the Save button")
    assert res.get("status") == "success", f"Visual action should succeed, got {res}"
    print(f"   [PASS] Executed visual click at coordinates {res.get('coordinates')}")
    print(f"          Spoken: '{res.get('spoken_response')}'")

    # 6. ComputerControl interface hook check
    print("\n6. Testing computer_control.visual_click hook...")
    assert hasattr(computer_control, "visual_click"), "computer_control must have visual_click"
    hook_res = computer_control.visual_click("Click search bar")
    assert hook_res.get("status") == "success"
    print("   [PASS] computer_control.visual_click verified.")

    print("\n==================================================")
    print("ALL OMNIPARSER INTEGRATION CHECKS PASSED NOMINAL")
    print("==================================================")

if __name__ == "__main__":
    test_omni_parser()
