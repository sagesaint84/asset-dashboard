import sys, json
sys.stdout.reconfigure(encoding='utf-8')
from app.services.pnl_records import import_pnl_file_data, read_pnl_records, get_pnl_summary

with open("내_매도실현손익.xlsx", "rb") as f:
    content = f.read()

# Import the file
records = import_pnl_file_data(content, "내_매도실현손익.xlsx")
print(f"Successfully imported {len(records)} records from 내_매도실현손익.xlsx!")

# Get summary
summary = get_pnl_summary(owner="모두", year="all", trade_type="all")
print(f"\n=== 매도 실현손익 집계 결과 (전체 기간) ===")
print(f"총 건수: {summary['record_count']:,d}건 (승리: {summary['win_count']}건, 손실: {summary['loss_count']}건)")
print(f"승률: {summary['win_rate']}%")
print(f"총 실현손익: {int(summary['total_pnl_krw']):,d}원")
print(f"가용 연도: {summary['available_years']}")

print("\n=== 연도별 실현손익 ===")
for y in summary['yearly_schedule']:
    print(f"[{y['year']}년] 총 실현손익: {int(y['total_krw']):>13,d}원 | 승: {int(y['win_krw']):>13,d}원 | 패: {int(y['loss_krw']):>13,d}원 | 건수: {len(y['items']):>3d}건")
