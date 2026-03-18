"""
场外信息 API 路由 - External Records API Routes

提供场外信息的 CRUD 接口，用于管理客户的线下消费和私域沟通记录
"""
from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from typing import List, Dict, Any, Optional
import logging
import csv
import io

from backend.analytics.external_analyzer import get_external_analyzer

router = APIRouter(prefix="/api/v2/external", tags=["external_records"])
analyzer = get_external_analyzer()


@router.get("/records")
async def get_records(
    search: Optional[str] = Query(None, description="按客户昵称搜索"),
    record_type: Optional[str] = Query(None, description="记录类型: communication/purchase"),
    channel: Optional[str] = Query(None, description="渠道筛选"),
    date_from: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量"),
    offset: int = Query(0, ge=0, description="偏移量")
) -> Dict[str, Any]:
    """
    获取场外记录列表（支持分页和筛选）

    Returns:
        {
            "records": [...],
            "total": int,
            "limit": int,
            "offset": int
        }
    """
    try:
        if record_type and record_type not in ['communication', 'purchase']:
            raise HTTPException(
                status_code=400,
                detail=f"无效的record_type: {record_type}. 必须是 communication 或 purchase"
            )

        result = analyzer.get_records(
            search=search,
            record_type=record_type,
            channel=channel,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            offset=offset
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[ExternalRoutes] get_records error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/records/{record_id}")
async def get_record(record_id: int) -> Dict[str, Any]:
    """获取单条场外记录"""
    try:
        record = analyzer.get_record_by_id(record_id)
        if not record:
            raise HTTPException(status_code=404, detail=f"记录 {record_id} 不存在")
        return record
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[ExternalRoutes] get_record error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/records")
async def create_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    创建场外记录

    Request Body:
        {
            "user_nick": str (必填),
            "record_type": "communication" | "purchase" (必填),
            "record_date": str (必填, YYYY-MM-DD),
            "channel": str (可选),
            "content": str (可选),
            "notes": str (可选),
            "amount": number (可选, 仅消费类型),
            "category": str (可选, 仅消费类型),
            "created_by": str (可选)
        }
    """
    try:
        # 验证必填字段
        required_fields = ['user_nick', 'record_type', 'record_date']
        for field in required_fields:
            if not record.get(field):
                raise HTTPException(
                    status_code=400,
                    detail=f"缺少必填字段: {field}"
                )

        # 验证记录类型
        if record.get('record_type') not in ['communication', 'purchase']:
            raise HTTPException(
                status_code=400,
                detail=f"无效的record_type: {record.get('record_type')}"
            )

        result = analyzer.create_record(
            user_nick=record.get('user_nick'),
            record_type=record.get('record_type'),
            record_date=record.get('record_date'),
            channel=record.get('channel'),
            content=record.get('content'),
            notes=record.get('notes'),
            amount=float(record.get('amount')) if record.get('amount') else None,
            category=record.get('category'),
            created_by=record.get('created_by')
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[ExternalRoutes] create_record error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/records/{record_id}")
async def update_record(record_id: int, record: Dict[str, Any]) -> Dict[str, Any]:
    """
    更新场外记录

    Request Body: 只包含需要更新的字段
    """
    try:
        # 检查记录是否存在
        existing = analyzer.get_record_by_id(record_id)
        if not existing:
            raise HTTPException(status_code=404, detail=f"记录 {record_id} 不存在")

        # 验证记录类型（如果提供）
        if record.get('record_type') and record.get('record_type') not in ['communication', 'purchase']:
            raise HTTPException(
                status_code=400,
                detail=f"无效的record_type: {record.get('record_type')}"
            )

        result = analyzer.update_record(
            record_id=record_id,
            user_nick=record.get('user_nick'),
            record_type=record.get('record_type'),
            record_date=record.get('record_date'),
            channel=record.get('channel'),
            content=record.get('content'),
            notes=record.get('notes'),
            amount=float(record.get('amount')) if record.get('amount') else None,
            category=record.get('category')
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[ExternalRoutes] update_record error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/records/{record_id}")
async def delete_record(record_id: int) -> Dict[str, Any]:
    """删除场外记录"""
    try:
        success = analyzer.delete_record(record_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"记录 {record_id} 不存在")
        return {"success": True, "message": f"记录 {record_id} 已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[ExternalRoutes] delete_record error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import")
async def import_records(
    file: UploadFile = File(...),
    created_by: Optional[str] = Query(None, description="录入人")
) -> Dict[str, Any]:
    """
    批量导入场外记录（CSV格式）

    CSV 格式要求:
    - 第一行为表头（必须包含：user_nick, record_type, record_date）
    - 可选字段：channel, content, notes, amount, category
    - record_type 必须是 communication 或 purchase
    - record_date 格式：YYYY-MM-DD
    """
    try:
        # 读取文件内容
        content = await file.read()

        # 尝试不同编码
        text_content = None
        for encoding in ['utf-8', 'gbk', 'gb2312']:
            try:
                text_content = content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue

        if text_content is None:
            raise HTTPException(
                status_code=400,
                detail="无法识别文件编码，请使用 UTF-8 或 GBK 编码"
            )

        # 解析 CSV
        reader = csv.DictReader(io.StringIO(text_content))
        records = []
        errors = []

        for i, row in enumerate(reader):
            try:
                # 验证必填字段
                if not row.get('user_nick'):
                    errors.append(f"第 {i + 2} 行: 缺少 user_nick")
                    continue
                if not row.get('record_type'):
                    errors.append(f"第 {i + 2} 行: 缺少 record_type")
                    continue
                if row.get('record_type') not in ['communication', 'purchase']:
                    errors.append(f"第 {i + 2} 行: record_type 必须是 communication 或 purchase")
                    continue
                if not row.get('record_date'):
                    errors.append(f"第 {i + 2} 行: 缺少 record_date")
                    continue

                record = {
                    "user_nick": row['user_nick'].strip(),
                    "record_type": row['record_type'].strip(),
                    "record_date": row['record_date'].strip(),
                    "channel": row.get('channel', '').strip() or None,
                    "content": row.get('content', '').strip() or None,
                    "notes": row.get('notes', '').strip() or None,
                    "amount": row.get('amount', '').strip() or None,
                    "category": row.get('category', '').strip() or None,
                    "created_by": created_by
                }
                records.append(record)
            except Exception as e:
                errors.append(f"第 {i + 2} 行: {str(e)}")

        if not records:
            raise HTTPException(
                status_code=400,
                detail=f"没有有效的记录可导入。错误: {errors[:5]}"
            )

        # 批量导入
        result = analyzer.batch_import(records, created_by)
        result["parse_errors"] = errors[:10]

        return result

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[ExternalRoutes] import_records error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/template")
async def export_template():
    """
    导出 CSV 导入模板

    返回一个 CSV 模板文件，包含示例数据和说明
    """
    try:
        from fastapi.responses import StreamingResponse

        template = """user_nick,record_type,record_date,channel,content,notes,amount,category
王小明,communication,2026-02-20,微信,咨询新品烟斗的到货时间,客户对新出的限量版很感兴趣,,
李女士,purchase,2026-02-18,北京SKP,购买限量版打火机,VIP客户赠送会员礼品,8500,Lighters
张先生,communication,2026-02-15,电话,投诉物流延迟问题,已跟进处理客户满意,,
"""

        output = io.BytesIO(template.encode('utf-8-sig'))  # BOM for Excel compatibility

        return StreamingResponse(
            output,
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=external_records_template.csv"
            }
        )
    except Exception as e:
        logging.error(f"[ExternalRoutes] export_template error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_statistics() -> Dict[str, Any]:
    """
    获取场外信息统计

    Returns:
        {
            "total_records": int,
            "communication_count": int,
            "purchase_count": int,
            "total_offline_amount": float,
            "top_channels": [...],
            "recent_records": [...]
        }
    """
    try:
        stats = analyzer.get_statistics()
        return stats
    except Exception as e:
        logging.error(f"[ExternalRoutes] get_statistics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_nick}")
async def get_user_records(
    user_nick: str,
    limit: int = Query(50, ge=1, le=200)
) -> List[Dict[str, Any]]:
    """
    获取某客户的所有场外记录

    用于 AI 分析时获取补充上下文
    """
    try:
        records = analyzer.get_records_by_user(user_nick, limit)
        return records
    except Exception as e:
        logging.error(f"[ExternalRoutes] get_user_records error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
