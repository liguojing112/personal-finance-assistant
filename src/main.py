"""
一键运行入口
支持处理单个文件或全部文件
用法：
    python src/main.py                     # 处理data/raw下所有文件
    python src/main.py --file 账单文件.xlsx # 处理指定文件
"""
import argparse
from pathlib import Path
import import_data
import classify
import report
import alert

def main():
    parser = argparse.ArgumentParser(description='个人财务小助手一键运行')
    parser.add_argument('--file', type=str, help='指定处理的原始账单文件路径（Excel）')
    args = parser.parse_args()
    
    # 步骤1：导入清洗
    if args.file:
        raw_path = Path(args.file)
        if not raw_path.exists():
            print(f"文件不存在: {raw_path}")
            return
        processed_dir = Path('data/processed')
        processed_dir.mkdir(parents=True, exist_ok=True)
        import_data.process_one_file(raw_path, processed_dir)
    else:
        import_data.import_all()
    
    # 步骤2：分类
    classify.classify_all()
    
    # 步骤3：生成报表（同时获得生成器）
    report_gen = report.generate_monthly_report()
    
    # 步骤4：超支提醒（会消费report_gen，并添加超支统计表）
    alert.alert_all(report_gen)
    
    print("所有任务完成！报表位于output/文件夹，超支记录见output/overbudget_details.csv")

if __name__ == '__main__':
    main()