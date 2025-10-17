import subprocess
import sys


def get_clipboard_content():
    if sys.platform == "darwin":  # macOS
        return subprocess.check_output("pbpaste", universal_newlines=True)
    elif sys.platform == "win32":  # Windows
        return subprocess.check_output(
            "powershell Get-Clipboard", universal_newlines=True
        )
    else:  # Linux
        return subprocess.check_output("xclip -o", universal_newlines=True)


def write_to_clipboard(content):
    if sys.platform == "darwin":  # macOS
        subprocess.run("pbcopy", universal_newlines=True, input=content)
    elif sys.platform == "win32":  # Windows
        subprocess.run(
            "powershell Set-Clipboard", universal_newlines=True, input=content
        )
    else:  # Linux
        subprocess.run(
            "xclip -selection clipboard", universal_newlines=True, input=content
        )


if __name__ == "__main__":
    # Example usage
    clipboard_content = get_clipboard_content()
    print(f"Clipboard content: {clipboard_content}")
    write_to_clipboard("New clipboard content!")
    clipboard_content = get_clipboard_content()
    print(f"Clipboard content: {clipboard_content}")
