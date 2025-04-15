    def get_system_menu(self):
        """返回系統功能選單的快速回覆"""
        items = [
            QuickReplyButton(
                action=MessageAction(label="清除對話記錄", text="清除對話記錄")
            ),
            QuickReplyButton(
                action=MessageAction(label="查看使用說明", text="查看使用說明")
            ),
            QuickReplyButton(
                action=MessageAction(label="使用規則", text="使用規則")
            ),
            QuickReplyButton(
                action=MessageAction(label="提供使用回饋", text="提供使用回饋")
            ),
            QuickReplyButton(
                action=MessageAction(label="返回主選單", text="主選單")
            )
        ]
        return QuickReply(items=items) 