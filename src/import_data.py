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
    """处理单个微信Excel文件，清洗后保存到processed，并返回DataFrame"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
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
    return df

def process_alipay_file(file_path, output_dir):
    """处理支付宝账单CSV文件，清洗后保存到processed，并返回DataFrame"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"正在处理支付宝账单: {file_path}")
    
    # 尝试用 GBK 编码读取，若失败则尝试 UTF-8
    encodings = ['gbk', 'utf-8']
    df = None
    for enc in encodings:
        try:
            # 找到表头行（以"交易时间"开头）
            with open(file_path, 'r', encoding=enc) as f:
                lines = f.readlines()
            
            header_line_index = None
            for i, line in enumerate(lines):
                if line.startswith('交易时间'):
                    header_line_index = i
                    break
            
            if header_line_index is None:
                raise ValueError("支付宝CSV文件中未找到交易时间表头")
            
            # 读取CSV，跳过前面的说明行
            df = pd.read_csv(file_path, skiprows=header_line_index, encoding=enc)
            print(f"成功使用编码 {enc} 读取文件")
            break  # 读取成功则退出循环
        except UnicodeDecodeError:
            print(f"编码 {enc} 失败，尝试下一个...")
            continue
    
    if df is None:
        raise ValueError("无法使用 GBK 或 UTF-8 编码读取文件，请检查文件格式")
    
    # 清理列名（去除空格）
    df.columns = [col.strip() for col in df.columns]
    
    # 列名映射到统一格式
    col_map = {
        '交易时间': 'tx_time',
        '交易分类': 'tx_type',
        '交易对方': 'counterparty',
        '商品说明': 'product',
        '收/支': 'income_expense',
        '金额': 'amount',
        '收/付款方式': 'payment',
        '交易状态': 'status',
        '交易订单号': 'tx_id',
        '商家订单号': 'merchant_id',
        '备注': 'remarks'
    }
    # 只保留映射中存在的列
    existing_cols = {k: v for k, v in col_map.items() if k in df.columns}
    df.rename(columns=existing_cols, inplace=True)
    
    # 确保所有标准列都存在
    standard_cols = ['tx_time', 'tx_type', 'counterparty', 'product', 'income_expense', 'amount', 'payment', 'status', 'tx_id', 'merchant_id', 'remarks']
    for col in standard_cols:
        if col not in df.columns:
            df[col] = ''
    
    df = df[standard_cols]
    
    # 金额转为浮点数
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0.0)
    
    # 转换交易时间为datetime
    df['tx_time'] = pd.to_datetime(df['tx_time'], errors='coerce')
    df = df.dropna(subset=['tx_time'])
    
    # 去重（按交易订单号）
    df = df.drop_duplicates(subset=['tx_id'], keep='first')
    
    # 重置索引
    df.reset_index(drop=True, inplace=True)
    
    # 保存为parquet
    base = Path(file_path).stem
    out_file = output_dir / f"{base}_alipay_cleaned.parquet"
    df.to_parquet(out_file, index=False)
    print(f"已保存支付宝清洗后数据到: {out_file}")
    return df

def import_all(raw_dir='data/raw', processed_dir='data/processed'):
    """批量处理raw_dir下所有.xlsx文件（兼容原有功能，但改为返回DataFrame列表）"""
    raw_path = Path(raw_dir)
    processed_path = Path(processed_dir)
    processed_path.mkdir(parents=True, exist_ok=True)
    
    xlsx_files = list(raw_path.glob('*.xlsx'))
    if not xlsx_files:
        print("raw文件夹中没有.xlsx文件")
        return []
    
    out_files = []
    dfs = []
    for f in xlsx_files:
        try:
            df = process_one_file(f, processed_path)
            dfs.append(df)
            out_files.append(f)
        except Exception as e:
            print(f"处理文件 {f} 时出错: {e}")
    return dfs

if __name__ == '__main__':
    import_all()