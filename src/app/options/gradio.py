# src/app/gradio_app.py
import gradio as gr
from .query import answer


def chat_with_bot(message, chat_history, product_name, strict_mode):
    """
    Xử lý từng lượt chat: gửi câu hỏi tới module answer()
    và gắn nguồn + chế độ strict.
    """
    # gọi hàm trả lời có metadata
    print("product_name:", product_name)
    # Nếu chọn "Tất cả" thì không filter
    filter_product = None if product_name == "Tất cả" else product_name
    out = answer(
        message,
        product_name=filter_product
    )

    # kết quả dạng tuple (reply, sources)
    if isinstance(out, tuple):
        reply, sources = out
    else:
        reply, sources = out, []

    # Strict mode: chỉ trả lời nếu có thông tin thật
    if strict_mode and (not reply or reply.lower().startswith("không có")):
        bot_reply = "Không có thông tin."
    else:
        # Gắn thêm “Nguồn tham khảo” nếu có
        if sources:
            src_md = "\n".join(sources)
            bot_reply = f"{reply}\n\n---\n**Nguồn tham khảo:**\n{src_md}"
        else:
            bot_reply = reply

    chat_history.append((message, bot_reply))
    return "", chat_history


# =================== GIAO DIỆN ===================
with gr.Blocks(theme="soft") as demo:
    gr.Markdown("## 🤖 Vertiv Chatbot — Hỗ trợ kỹ thuật Vertiv")

    # Input cho người dùng
    with gr.Row():
        product = gr.Dropdown(
            label="Chọn sản phẩm",
            choices=[
                "Tất cả",
                "Netsure 210",
                "Netsure 531", 
                "Netsure 731",
                "Liebert Apm",
                "Liebert Exs",
                "Liebrt Mtp",
                "Liebert Crv",
                "Libert Pex3",
                "Libert Pex4"
            ],
            value="Tất cả",
            interactive=True
        )
        # Tắt strict mode mặc định + cho phép bật/tắt
        strict = gr.Checkbox(
            label="Strict mode (chỉ trả lời nếu có dữ liệu thật)",
            value=False,
            interactive=True
        )

    chatbot = gr.Chatbot(label="💬 Chat Vertiv", height=420)
    msg = gr.Textbox(label="Nhập câu hỏi của bạn...")

    def respond(message, chat_history, product_name, strict_mode):
        return chat_with_bot(message, chat_history, product_name, strict_mode)

    msg.submit(respond, [msg, chatbot, product, strict], [msg, chatbot])

# =================== KHỞI CHẠY ===================
if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)