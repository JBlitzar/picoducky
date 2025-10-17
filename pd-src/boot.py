import usb_cdc
import usb_hid

# Enable composite USB: CDC (data) + HID (keyboard + mouse)
usb_cdc.enable(console=False, data=True)
usb_hid.enable((usb_hid.Device.KEYBOARD, usb_hid.Device.MOUSE))
