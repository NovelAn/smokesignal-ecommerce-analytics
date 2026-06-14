"""
测试 Inventory Inquiry Intent 识别准确率

从 chat_history 表筛选 10-20 个包含库存关键词的客户，
手动触发 AI 分析,验证识别准确率是否 >= 80%。
"""
import asyncio
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.database.connection import Database
from backend.ai.analyzer_orchestrator import AnalyzerOrchestrator

INVENTORY_KEYWORDS = [
    "缺货", "断货", "没货", "有货吗", "什么时候有",
    "补货", "库存", "有现货吗", "到货"
]

async def find_test_samples():
    """从 chat_history 筛选包含库存关键词的客户"""
    db = Database()

    # 构建 LIKE 条件
    conditions = " OR ".join([f"message_content LIKE '%{kw}%'" for kw in INVENTORY_KEYWORDS])

    query = f"""
    SELECT DISTINCT buyer_nick, COUNT(*) as msg_count
    FROM chat_history
    WHERE sender = 'buyer' AND ({conditions})
    GROUP BY buyer_nick
    ORDER BY msg_count DESC
    LIMIT 20
    """

    samples = db.execute_query(query)
    return samples

async def test_intent_recognition():
    """对样本客户运行 AI 分析并统计结果"""
    samples = await find_test_samples()
    print(f"Found {len(samples)} test samples")

    orchestrator = AnalyzerOrchestrator()
    results = []

    for sample in samples:
        buyer_nick = sample['buyer_nick']
        print(f"\nAnalyzing {buyer_nick}...")

        try:
            # 强制刷新 AI 分析
            analysis = await orchestrator.analyze_customer_full(
                buyer_nick=buyer_nick,
                force_refresh=True
            )

            dominant_intent = analysis.get('dominant_intent', 'Unknown')
            intent_dist = analysis.get('intent_distribution', {})
            inventory_score = intent_dist.get('Inventory Inquiry', 0.0)

            results.append({
                'buyer_nick': buyer_nick,
                'dominant_intent': dominant_intent,
                'inventory_score': inventory_score,
                'is_inventory': dominant_intent == 'Inventory Inquiry' or inventory_score > 0.3
            })

            print(f"  Dominant Intent: {dominant_intent}")
            print(f"  Inventory Score: {inventory_score:.2f}")

        except Exception as e:
            print(f"  Error: {e}")
            results.append({
                'buyer_nick': buyer_nick,
                'error': str(e)
            })

    # 统计准确率
    total = len([r for r in results if 'error' not in r])
    correct = len([r for r in results if r.get('is_inventory', False)])
    accuracy = correct / total * 100 if total > 0 else 0

    print(f"\n{'='*50}")
    print(f"Total samples: {total}")
    print(f"Identified as Inventory Inquiry: {correct}")
    print(f"Accuracy: {accuracy:.1f}%")
    print(f"{'='*50}")

    if accuracy >= 80:
        print("✅ Test PASSED - Accuracy >= 80%")
    else:
        print("❌ Test FAILED - Accuracy < 80%, need to adjust prompt")

    return results

if __name__ == "__main__":
    asyncio.run(test_intent_recognition())
