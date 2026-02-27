"""
基于用户自定义规则的自动分类模块
读取category_rules.json，对每笔支出打上类别标签
"""
import json
import pandas as pd
from pathlib import Path

def load_rules(rules_path='config/category_rules.json'):
    """加载分类规则"""
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

def add_category_column(df, rules_path='config/category_rules.json'):
    """为DataFrame添加category列"""
    rules = load_rules(rules_path)
    df['category'] = df.apply(lambda row: classify_transaction(row, rules), axis=1)
    return df

def classify_all(processed_dir='data/processed', rules_path='config/category_rules.json'):
    """为processed下所有清洗过的文件添加分类，并覆盖保存"""
    processed_path = Path(processed_dir)
    for parquet_file in processed_path.glob('*_cleaned.parquet'):
        print(f"正在分类: {parquet_file}")
        df = pd.read_parquet(parquet_file)
        df = add_category_column(df, rules_path)
        # 保存回原文件（或可另存为带类别的文件）
        df.to_parquet(parquet_file, index=False)
        print(f"分类完成，已更新: {parquet_file}")

if __name__ == '__main__':
    classify_all()