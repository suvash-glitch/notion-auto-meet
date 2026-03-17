"""Generate a PyInstaller version info file."""

VERSION_INFO = """
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(1, 0, 0, 0),
    prodvers=(1, 0, 0, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          u'040904B0',
          [
            StringStruct(u'CompanyName', u'Notion Auto-Meet'),
            StringStruct(u'FileDescription', u'Notion Auto-Meet - Auto-click Start Transcribing'),
            StringStruct(u'FileVersion', u'1.0.0.0'),
            StringStruct(u'InternalName', u'NotionAutoMeet'),
            StringStruct(u'OriginalFilename', u'NotionAutoMeet.exe'),
            StringStruct(u'ProductName', u'Notion Auto-Meet'),
            StringStruct(u'ProductVersion', u'1.0.0.0'),
            StringStruct(u'LegalCopyright', u'MIT License'),
          ]
        )
      ]
    ),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
"""

if __name__ == "__main__":
    with open("installer/version_info.txt", "w") as f:
        f.write(VERSION_INFO.strip())
    print("Generated installer/version_info.txt")
