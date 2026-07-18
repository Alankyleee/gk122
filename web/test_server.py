import unittest

from camera_selection import (
    is_gk122_camera_name,
    is_virtual_camera_name,
    select_gk122_device,
)


class CameraSelectionTests(unittest.TestCase):
    def test_virtual_camera_names_are_rejected(self):
        self.assertTrue(is_virtual_camera_name("OBS Virtual Camera"))
        self.assertTrue(is_virtual_camera_name("ManyCam Virtual Webcam"))
        self.assertFalse(is_virtual_camera_name("GK122 Document Camera"))

    def test_gk122_names_are_recognized(self):
        self.assertTrue(is_gk122_camera_name("GK122 USB Camera"))
        self.assertTrue(is_gk122_camera_name("得力高拍仪"))
        self.assertFalse(is_gk122_camera_name("Integrated Webcam"))

    def test_auto_selection_never_returns_virtual_camera(self):
        devices = [
            {"name": "OBS Virtual Camera", "is_gk122": True, "is_virtual": True, "score": 999},
            {"name": "GK122", "is_gk122": True, "is_virtual": False, "score": 140},
        ]
        self.assertEqual(select_gk122_device(devices)["name"], "GK122")

    def test_auto_selection_returns_none_without_gk122(self):
        devices = [
            {"name": "Integrated Webcam", "is_gk122": False, "is_virtual": False, "score": 0},
        ]
        self.assertIsNone(select_gk122_device(devices))


if __name__ == "__main__":
    unittest.main()
