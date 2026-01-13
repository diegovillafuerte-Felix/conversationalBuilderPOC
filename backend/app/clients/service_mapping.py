"""Maps tool names to service endpoints.

This module defines the mapping between tool names (as used by the LLM)
and their corresponding HTTP endpoints in the services gateway.

Format: "tool_name": ("HTTP_METHOD", "/api/v1/path/to/endpoint")

Path parameters are enclosed in braces: /api/v1/resource/{resource_id}
These will be substituted from the params dict at runtime.
"""

# Maps tool names to (HTTP_METHOD, endpoint_path)
SERVICE_MAPPING = {
    # ==================== Remittances ====================
    "get_corridors": ("GET", "/api/v1/remittances/corridors"),
    "get_exchange_rate": ("GET", "/api/v1/remittances/exchange-rate"),
    "create_quote": ("POST", "/api/v1/remittances/quotes"),
    "list_recipients": ("GET", "/api/v1/remittances/recipients"),
    "get_recipient": ("GET", "/api/v1/remittances/recipients/{recipient_id}"),
    "add_recipient": ("POST", "/api/v1/remittances/recipients"),
    "save_recipient": ("POST", "/api/v1/remittances/recipients"),
    "add_delivery_method": ("POST", "/api/v1/remittances/recipients/{recipient_id}/delivery-methods"),
    "save_delivery_method": ("POST", "/api/v1/remittances/recipients/{recipient_id}/delivery-methods"),
    "delete_recipient": ("DELETE", "/api/v1/remittances/recipients/{recipient_id}"),
    "get_delivery_methods": ("GET", "/api/v1/remittances/delivery-methods"),
    "get_user_limits": ("GET", "/api/v1/remittances/limits"),
    "create_transfer": ("POST", "/api/v1/remittances/transfers"),
    "get_transfer_status": ("GET", "/api/v1/remittances/transfers/{transfer_id}"),
    "list_transfers": ("GET", "/api/v1/remittances/transfers"),
    "cancel_transfer": ("POST", "/api/v1/remittances/transfers/{transfer_id}/cancel"),
    "create_snpl_transfer": ("POST", "/api/v1/remittances/snpl-transfers"),
    "get_quick_send_options": ("GET", "/api/v1/remittances/quick-send"),
    # Legacy aliases
    "get_recipients": ("GET", "/api/v1/remittances/recipients"),
    "calculate_transfer": ("POST", "/api/v1/remittances/quotes"),
    "get_recent_transfers": ("GET", "/api/v1/remittances/transfers"),

    # ==================== SNPL (Send Now Pay Later) ====================
    "get_snpl_eligibility": ("GET", "/api/v1/snpl/eligibility"),
    "get_eligibility": ("GET", "/api/v1/snpl/eligibility"),
    "calculate_terms": ("POST", "/api/v1/snpl/calculate"),
    "submit_snpl_application": ("POST", "/api/v1/snpl/applications"),
    "apply_for_snpl": ("POST", "/api/v1/snpl/applications"),
    "get_snpl_overview": ("GET", "/api/v1/snpl/overview"),
    "get_overview": ("GET", "/api/v1/snpl/overview"),
    "get_loan_details": ("GET", "/api/v1/snpl/loans/{loan_id}"),
    "list_loans": ("GET", "/api/v1/snpl/loans"),
    "get_payment_schedule": ("GET", "/api/v1/snpl/loans/{loan_id}/schedule"),
    "get_payment_history": ("GET", "/api/v1/snpl/payments"),
    "make_snpl_payment": ("POST", "/api/v1/snpl/payments"),
    "make_payment": ("POST", "/api/v1/snpl/payments"),
    "use_credit_for_remittance": ("POST", "/api/v1/snpl/loans/{loan_id}/use-for-remittance"),

    # ==================== TopUps ====================
    "get_carriers": ("GET", "/api/v1/topups/carriers"),
    "get_carrier": ("GET", "/api/v1/topups/carriers/{carrier_id}"),
    "get_frequent_numbers": ("GET", "/api/v1/topups/frequent-numbers"),
    "detect_carrier": ("POST", "/api/v1/topups/detect-carrier"),
    "get_carrier_plans": ("GET", "/api/v1/topups/carriers/{carrier_id}/plans"),
    "get_topup_price": ("GET", "/api/v1/topups/price"),
    "send_topup": ("POST", "/api/v1/topups"),
    "get_topup_history": ("GET", "/api/v1/topups/history"),

    # ==================== BillPay ====================
    "get_billers": ("GET", "/api/v1/billpay/billers"),
    "get_biller": ("GET", "/api/v1/billpay/billers/{biller_id}"),
    "get_saved_billers": ("GET", "/api/v1/billpay/saved"),
    "get_bill_details": ("GET", "/api/v1/billpay/billers/{biller_id}/details"),
    "calculate_payment": ("POST", "/api/v1/billpay/calculate"),
    "pay_bill": ("POST", "/api/v1/billpay/payments"),
    "save_biller": ("POST", "/api/v1/billpay/saved"),
    # Note: get_payment_history is also in SNPL, billpay's is for bill payments

    # ==================== Wallet ====================
    "get_balance": ("GET", "/api/v1/wallet/balance"),
    "get_payment_methods": ("GET", "/api/v1/wallet/payment-methods"),
    "add_funds": ("POST", "/api/v1/wallet/add-funds"),
    "get_transactions": ("GET", "/api/v1/wallet/transactions"),
    "add_payment_method": ("POST", "/api/v1/wallet/payment-methods"),
    "remove_payment_method": ("DELETE", "/api/v1/wallet/payment-methods/{payment_method_id}"),

    # ==================== Financial Data ====================
    "get_user_financial_summary": ("GET", "/api/v1/financial-data/summary"),
    "get_rate_trends": ("GET", "/api/v1/financial-data/rate-trends"),
    "get_fee_optimization_tips": ("GET", "/api/v1/financial-data/optimization-tips"),
    "get_spending_analysis": ("GET", "/api/v1/financial-data/spending-analysis"),
    "get_savings_recommendations": ("GET", "/api/v1/financial-data/savings-recommendations"),

    # ==================== Campaigns ====================
    "get_active_campaigns": ("GET", "/api/v1/campaigns/active"),
    "get_campaign_by_id": ("GET", "/api/v1/campaigns/{campaign_id}"),
    "check_user_eligibility": ("GET", "/api/v1/campaigns/{campaign_id}/eligibility"),
    "record_campaign_impression": ("POST", "/api/v1/campaigns/impressions"),
    "get_campaigns_for_context": ("GET", "/api/v1/campaigns/by-context"),
    "get_user_campaign_history": ("GET", "/api/v1/campaigns/history"),
}


def get_endpoint_for_tool(tool_name: str) -> tuple:
    """Get the HTTP method and endpoint for a tool.

    Args:
        tool_name: Name of the tool

    Returns:
        Tuple of (HTTP_METHOD, endpoint_path) or None if not found
    """
    return SERVICE_MAPPING.get(tool_name)
