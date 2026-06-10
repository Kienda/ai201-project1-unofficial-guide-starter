"""Gradio interface for the CULPA professor review guide."""

from __future__ import annotations

import gradio as gr

from rag_pipeline import ask


def handle_query(question: str) -> tuple[str, str]:
    question = question.strip()
    if not question:
        return "Enter a question about the collected CULPA CS professor reviews.", ""

    result = ask(question)
    sources = "\n".join(f"- {source}" for source in result["sources"])
    return result["answer"], sources


with gr.Blocks(title="Unofficial Guide: Columbia CS Professor Reviews") as demo:
    gr.Markdown("# Unofficial Guide: Columbia CS Professor Reviews")
    question = gr.Textbox(
        label="Question",
        placeholder="What do students say about Adam Cannon's workload?",
        lines=2,
    )
    ask_button = gr.Button("Ask")
    answer = gr.Textbox(label="Answer", lines=10)
    sources = gr.Textbox(label="Retrieved sources", lines=8)

    ask_button.click(handle_query, inputs=question, outputs=[answer, sources])
    question.submit(handle_query, inputs=question, outputs=[answer, sources])


if __name__ == "__main__":
    demo.launch()
