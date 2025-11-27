Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

' Lấy đường dẫn thư mục chứa file này
CurrentPath = FSO.GetParentFolderName(WScript.ScriptFullName)

' Đặt thư mục làm việc để tránh lỗi đường dẫn
WshShell.CurrentDirectory = CurrentPath

' Chạy file run_crane_app.bat ở chế độ ẩn (số 0 ở cuối lệnh)
' Nếu muốn hiện lại để sửa lỗi, hãy đổi số 0 thành số 1
WshShell.Run chr(34) & "run_crane_app.bat" & chr(34), 0

Set WshShell = Nothing