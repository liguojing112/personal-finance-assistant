"""
账单导入与清洗模块
支持批量导入原始微信账单Excel文件，清洗后保存为parquet格式到processed文件夹
"""
import pandas as pd
import os
import re
from pathlib import Path
import glob

def find_header_row(df):
    """查找表头行（包含'交易时间'的行）"""
    for i, row in df.iterrows():
        if '交易时间' in row.values:
            return i
    return None

def clean_amount(amount_str):
    """将金额字符串（如'¥2.00'）转换为浮点数"""
    if pd.isna(amount_str):
        return 0.0
    s = str(amount_str).replace('¥', '').replace(',', '').strip()
    try:
        return float(s)
    except:
        return 0.0

def process_one_file(file_path, output_dir):
    """处理单个Excel文件，清洗后保存到processed"""
    print(f"正在处理: {file_path}")
    df_raw = pd.read_excel(file_path, header=None, dtype=str)
    
    # 查找表头行
    header_row = find_header_row(df_raw)
    if header_row is None:
        raise ValueError(f"文件 {file_path} 中未找到交易时间列")
    
    # 设置列名，跳过前面的说明行
    df = pd.read_excel(file_path, header=header_row, dtype=str)
    
    # 列名标准化（去除空格，统一英文）
    df.columns = [col.strip() for col in df.columns]
    col_map = {
        '交易时间': 'tx_time',
        '交易类型': 'tx_type',
        '交易对方': 'counterparty',
        '商品': 'product',
        '收/支': 'income_expense',
        '金额(元)': 'amount',
        '支付方式': 'payment',
        '当前状态': 'status',
        '交易单号': 'tx_id',
        '商户单号': 'merchant_id',
        '备注': 'remarks'
    }
    df.rename(columns=col_map, inplace=True)
    
    # 只保留必要的列，防止缺失
    required_cols = ['tx_time', 'tx_type', 'counterparty', 'product', 'income_expense', 'amount']
    for col in required_cols:
        if col not in df.columns:
            df[col] = ''
    
    # 清洗金额
    df['amount_raw'] = df['amount']  # 保留原始字符串
    df['amount'] = df['amount'].apply(clean_amount)
    
    # 转换交易时间为datetime
    df['tx_time'] = pd.to_datetime(df['tx_time'], errors='coerce')
    df = df.dropna(subset=['tx_time'])  # 丢弃无法解析时间的行
    
    # 过滤有效交易（通常状态为支付成功或对方已收钱）
    valid_status = ['支付成功', '对方已收钱', '已转账', '已存入零钱']
    df = df[df['status'].isin(valid_status) | df['status'].isna()]  # 收入类可能无状态
    
    # 去重（按交易单号）
    df = df.drop_duplicates(subset=['tx_id'], keep='first')
    
    # 重置索引
    df.reset_index(drop=True, inplace=True)
    
    # 生成输出文件名
    base = Path(file_path).stem
    out_file = output_dir / f"{base}_cleaned.parquet"
    df.to_parquet(out_file, index=False)
    print(f"已保存清洗后数据到: {out_file}")
    return out_file

def import_all(raw_dir='data/raw', processed_dir='data/processed'):
    """批量处理raw_dir下所有.xlsx文件"""
    raw_path = Path(raw_dir)
    processed_path = Path(processed_dir)
    processed_path.mkdir(parents=True, exist_ok=True)
    
    xlsx_files = list(raw_path.glob('*.xlsx'))
    if not xlsx_files:
        print("raw文件夹中没有.xlsx文件")
        return []
    
    out_files = []
    for f in xlsx_files:
        try:
            out = process_one_file(f, processed_path)
            out_files.append(out)
        except Exception as e:
            print(f"处理文件 {f} 时出错: {e}")
    return out_files

if __name__ == '__main__':
    import_all()