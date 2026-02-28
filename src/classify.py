"""
基于用户自定义规则的自动分类模块
读取category_rules.json，对每笔支出打上类别标签
"""
import json
import pandas as pd
from pathlib import Path

def load_rules(rules_path=None):
    """加载分类规则，支持相对路径或绝对路径"""
    if rules_path is None:
        # 获取当前文件（classify.py）所在目录的父目录（项目根目录）
        base_dir = Path(__file__).parent.parent
        rules_path = base_dir / 'config' / 'category_rules.json'
    else:
        rules_path = Path(rules_path)
    
    with open(rules_path, 'r', encoding='utf-8') as f:
        rules = json.load(f)
    return rules

def classify_transaction(row, rules):
    """对单笔交易进行分类，返回类别名称"""
    # 只对支出分类
    if row['income_expense'] != '支出':
        return None
    
    # 合并需要匹配的字段
    text = f"{row['counterparty']} {row['product']} {row['remarks']}".lower()
    
    for category, keywords in rules.items():
        for kw in keywords:
            if kw.lower() in text:
                return category
    return '其他'

def add_category_column(df, rules_path=None):
    """为DataFrame添加category列"""
    rules = load_rules(rules_path)
    df['category'] = df.apply(lambda row: classify_transaction(row, rules), axis=1)
    return df

def classify_all(processed_dir='data/processed', rules_path=None):
    """为processed下所有清洗过的文件添加分类，并覆盖保存"""
    processed_path = Path(processed_dir)
    for parquet_file in processed_path.glob('*_cleaned.parquet'):
        print(f"正在分类: {parquet_file}")
        df = pd.read_parquet(parquet_file)
        df = add_category_column(df, rules_path)   # rules_path 为 None，自动定位根目录
        df.to_parquet(parquet_file, index=False)
        print(f"分类完成，已更新: {parquet_file}")

if __name__ == '__main__':
    classify_all()