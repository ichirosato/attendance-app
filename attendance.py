import csv
from datetime import date

# 今日の日付を取得
today = date.today().isoformat()

# 出席した授業名（まずは固定）
class_name = "経済学"

# CSVに1行追加
with open("attendance.csv", mode="a", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow([class_name, today])

print(f"{class_name} の出席を {today} として記録しました")