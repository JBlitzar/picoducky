import usb_cdc  # type: ignore
import usb_hid  # type: ignore

# Enable composite USB: CDC (data) + HID (keyboard + mouse)
usb_cdc.enable(console=False, data=True)

# https://gist.github.com/bitboy85/cdcd0e7e04082db414b5f1d23ab09005
absolute_mouse = usb_hid.Device(
    report_descriptor=bytes(
        # Absolute mouse
        (0x05, 0x01)  # Usage Page (Generic Desktop)
        + (0x09, 0x02)  # Usage (Mouse)
        + (0xA1, 0x01)  # Collection (Application)
        + (0x09, 0x01)  # Usage (Pointer)
        + (0xA1, 0x00)  # Collection (Physical)
        + (0x85, 0x0B)  # Report ID [11]
        # Buttons
        + (0x05, 0x09)  # Usage Page (Button)
        + (0x19, 0x01)  # Usage Minimum (0x01)
        + (0x29, 0x05)  # Usage Maximum (0x05)
        + (0x15, 0x00)  # Logical Minimum (0)
        + (0x25, 0x01)  # Logical Maximum (1)
        + (0x95, 0x05)  # Report Count (5)
        + (0x75, 0x01)  # Report Size (1)
        + (0x81, 0x02)  # Input (Data,Var,Abs)
        + (0x75, 0x03)  # Report Size (3)
        + (0x95, 0x01)  # Report Count (1)
        + (0x81, 0x03)  # Input (Const) - padding
        # Movement (Absolute positioning)
        + (0x05, 0x01)  # Usage Page (Generic Desktop)
        + (0x09, 0x30)  # Usage (X)
        + (0x09, 0x31)  # Usage (Y)
        + (0x15, 0x00)  # Logical Minimum (0)
        + (0x26, 0xFF, 0x7F)  # Logical Maximum (32767)
        + (0x75, 0x10)  # Report Size (16)
        + (0x95, 0x02)  # Report Count (2)
        + (0x81, 0x02)  # Input (Data,Var,Abs) - ABSOLUTE positioning!
        # Wheel
        + (0x09, 0x38)  # Usage (Wheel)
        + (0x15, 0x81)  # Logical Minimum (-127)
        + (0x25, 0x7F)  # Logical Maximum (127)
        + (0x75, 0x08)  # Report Size (8)
        + (0x95, 0x01)  # Report Count (1)
        + (0x81, 0x06)  # Input (Data,Var,Rel)
        + (0xC0,)  # End Collection
        + (0xC0,)  # End Collection
    ),
    usage_page=1,
    usage=2,
    in_report_lengths=(6,),  # 1 byte buttons + 2 bytes X + 2 bytes Y + 1 byte wheel
    out_report_lengths=(0,),
    report_ids=(11,),
)

# Enable keyboard and absolute mouse
usb_hid.enable((usb_hid.Device.KEYBOARD, absolute_mouse))
