#!/bin/bash
# 快速启动和测试脚本

echo "=========================================="
echo "  AI增强分析系统 - 快速启动"
echo "=========================================="

# 1. 检查依赖
echo ""
echo "步骤 1: 检查依赖..."
python -c "import openai; print('✅ OpenAI库已安装')" 2>/dev/null || {
    echo "❌ 缺少依赖，正在安装..."
    pip install openai -q
}

# 2. 检查API密钥
echo ""
echo "步骤 2: 检查API密钥..."
if grep -q "DEEPSEEK_API_KEY=sk-" .env 2>/dev/null; then
    echo "✅ DeepSeek API密钥已配置"
else
    echo "❌ 未找到DeepSeek API密钥"
    echo "请在.env文件中设置 DEEPSEEK_API_KEY"
    exit 1
fi

# 3. 启动后端
echo ""
echo "步骤 3: 启动后端服务..."
echo "在新终端窗口中运行以下命令："
echo ""
echo "  cd backend"
echo "  python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"
echo ""

read -p "按Enter键继续后端已启动..."

# 4. 运行测试
echo ""
echo "步骤 4: 运行AI分析测试..."
python scripts/test_ai_analysis.py

echo ""
echo "步骤 5: 运行API集成测试..."
python scripts/test_api_integration.py

echo ""
echo "=========================================="
echo "  测试完成！"
echo "=========================================="
echo ""
echo "查看AI系统状态："
echo "  curl http://localhost:8000/api/v2/ai/status"
echo ""
echo "测试API："
echo "  curl 'http://localhost:8000/api/v2/buyers/贺子洋715?include_ai=true'"
echo ""
