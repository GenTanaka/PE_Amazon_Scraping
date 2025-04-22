import pandas as pd

def remove_duplicate_emails(input_file, output_file):
    # CSVファイルを読み込む
    df = pd.read_csv(input_file)
    
    # メールアドレス列で重複を削除（最初の出現を保持）
    df_cleaned = df.drop_duplicates(subset=['ブランド'], keep='first')
    
    # 結果を新しいCSVファイルに保存
    df_cleaned.to_csv(output_file, index=False)
    print(f"重複削除前の行数: {len(df)}")
    print(f"重複削除後の行数: {len(df_cleaned)}")
    print(f"削除された重複行数: {len(df) - len(df_cleaned)}")

if __name__ == "__main__":
    input_file = "./csv/backpack.csv"
    output_file = "./csv/backpack_cleaned.csv"
    remove_duplicate_emails(input_file, output_file)
