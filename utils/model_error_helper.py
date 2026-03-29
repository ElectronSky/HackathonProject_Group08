"""
模型调用异常的统一归一化工具。

设计说明：
- 当前项目同时有“记账页 agent”和“财商页 agent”；
- 它们都依赖外部模型服务，因此同类异常不应该在多个页面里各写一套散乱处理逻辑；
- 这里把外部模型错误整理成统一的用户可读信息，便于 agent 层直接做优雅降级。
"""

from __future__ import annotations

from typing import Any


def _safe_lower_text(value: Any) -> str:
    """
    把任意异常对象安全转换成小写字符串，便于做关键词判断。
    """
    try:
        return str(value).lower()
    except Exception:
        return ""


def normalize_model_error(error: Exception) -> dict:
    """
    将模型调用异常归一化成前端可展示的结构。

    Returns:
        dict: 统一错误信息，包含：
            - error_type: 错误类型标识
            - status_message: 过程区显示文案
            - user_message: 聊天区最终回复文案
            - raw_error: 原始错误字符串，便于日志或调试
    """
    raw_error = str(error)
    lowered_error = _safe_lower_text(error)

    # 先处理当前最容易影响 demo 的账单欠费问题。
    if "arrearage" in lowered_error or "overdue-payment" in lowered_error:
        return {
            "error_type": "arrearage",
            "status_message": "❌ 当前模型服务暂时不可用：模型账号可能存在欠费或账单异常。",
            "user_message": (
                "我当前暂时无法继续调用大模型完成这次回答，因为模型服务账号可能存在欠费或账单异常。\n\n"
                "你现在可以这样理解这个问题：\n"
                "- 页面和流程本身没有完全坏掉；\n"
                "- 当前是外部模型服务被拒绝访问，所以这次无法继续生成 AI 回复；\n"
                "- 处理方式通常是检查阿里云百炼 / 通义模型服务账户是否欠费、余额不足或被停用。\n\n"
                "等模型服务恢复后，你可以再次发送同一个问题继续使用。"
            ),
            "raw_error": raw_error,
        }

    # 再处理常见的网络或 API 服务不可用问题。
    if any(keyword in lowered_error for keyword in ["timeout", "timed out", "connection", "network", "unavailable"]):
        return {
            "error_type": "network_or_service",
            "status_message": "❌ 当前模型服务连接异常，可能是网络波动或外部接口暂时不可用。",
            "user_message": (
                "我刚才在调用模型服务时遇到了连接异常，所以这次没能顺利生成回答。\n\n"
                "你可以稍后重试一次；如果多次都这样，建议检查当前网络环境或外部模型服务状态。"
            ),
            "raw_error": raw_error,
        }

    # 最后给一个通用但仍然用户友好的兜底。
    return {
        "error_type": "unknown_model_error",
        "status_message": "❌ 当前模型服务发生异常，本次回答已被中断。",
        "user_message": (
            "我刚才在调用模型服务时遇到了异常，所以这次没能顺利完成回答。\n\n"
            "这通常不是你输入的问题本身，而是外部模型服务在当前时刻不可用。"
            "你可以稍后重新试一次。"
        ),
        "raw_error": raw_error,
    }

