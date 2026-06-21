from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from pypdf import PdfReader, PdfWriter
from datetime import datetime
import fitz  # PyMuPDF
import os, io, traceback

app = Flask(__name__)

# Origens permitidas a chamar este back-end.
# Inclui o ambiente local de desenvolvimento e a URL do GitHub Pages.
CORS(app, origins=[
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "https://matheusdev521.github.io",
])

BASE = os.path.dirname(os.path.abspath(__file__))


@app.route("/gerar-png", methods=["POST"])
def gerar_png():
    try:
        dados = request.get_json()

        semana_raw = dados.get("semana", "")
        locais     = dados.get("locais", [])
        designacao = dados.get("designacao", {})

        try:
            semana = datetime.strptime(semana_raw, "%Y-%m-%d").strftime("%d/%m/%Y")
        except ValueError:
            semana = semana_raw

        input_path = os.path.join(BASE, "designacao.pdf")

        doc = fitz.open(input_path)
        page = doc[0]

        checkbox_map = {
            "900_5_CheckBox": "principal",
            "900_6_CheckBox": "salaB",
            "900_7_CheckBox": "salaC",
        }

        texto_map = {
            "900_1_Text_SanSerif": designacao.get("nome", ""),
            "900_2_Text_SanSerif": designacao.get("ajudante", ""),
            "900_3_Text_SanSerif": semana,
            "900_4_Text_SanSerif": f"{designacao.get('numero', '')}. {designacao.get('parte', '')}".strip(". "),
        }

        for widget in page.widgets():
            nome = widget.field_name

            if nome in texto_map:
                widget.field_value = texto_map[nome]
                widget.update()

            elif nome in checkbox_map:
                local = checkbox_map[nome]
                widget.field_value = widget.on_state() if local in locais else False
                widget.update()

        # Renderiza direto para PNG via PyMuPDF (sem Poppler)
        mat = fitz.Matrix(300 / 72, 300 / 72)  # 300 dpi
        pix = page.get_pixmap(matrix=mat, alpha=False)

        img_buffer = io.BytesIO(pix.tobytes("png"))
        img_buffer.seek(0)
        doc.close()

        return send_file(
            img_buffer,
            mimetype="image/png",
            as_attachment=False,
            download_name="designacao.png"
        )

    except Exception as e:
        traceback.print_exc()
        return jsonify({"erro": str(e)}), 500


@app.route("/gerar-pdf", methods=["POST"])
def gerar_pdf():
    try:
        dados = request.get_json()

        semana_raw  = dados.get("semana", "")
        locais      = dados.get("locais", [])
        designacoes = dados.get("designacoes", [])

        try:
            semana = datetime.strptime(semana_raw, "%Y-%m-%d").strftime("%d/%m/%Y")
        except ValueError:
            semana = semana_raw

        pdfs_gerados = []

        for d in designacoes:
            input_path = os.path.join(BASE, "designacao.pdf")
            reader = PdfReader(input_path)
            writer = PdfWriter()
            writer.append(reader)

            campos = {
                "900_1_Text_SanSerif": d.get("nome", ""),
                "900_2_Text_SanSerif": d.get("ajudante", ""),
                "900_3_Text_SanSerif": semana,
                "900_4_Text_SanSerif": f"{d.get('numero', '')}. {d.get('parte', '')}".strip(". "),
                "900_5_CheckBox": "/Yes" if "principal" in locais else "/Off",
                "900_6_CheckBox": "/Yes" if "salaB"     in locais else "/Off",
                "900_7_CheckBox": "/Yes" if "salaC"     in locais else "/Off",
            }

            writer.update_page_form_field_values(
                writer.pages[0], campos, auto_regenerate=False
            )

            buffer = io.BytesIO()
            writer.write(buffer)
            pdfs_gerados.append(buffer.getvalue())

        if len(pdfs_gerados) == 1:
            return send_file(
                io.BytesIO(pdfs_gerados[0]),
                mimetype="application/pdf",
                as_attachment=True,
                download_name="designacao.pdf"
            )

        merged_writer = PdfWriter()
        for pdf_bytes in pdfs_gerados:
            merged_writer.append(PdfReader(io.BytesIO(pdf_bytes)))

        output = io.BytesIO()
        merged_writer.write(output)
        output.seek(0)

        return send_file(
            output,
            mimetype="application/pdf",
            as_attachment=True,
            download_name="designacoes.pdf"
        )

    except Exception as e:
        traceback.print_exc()
        return jsonify({"erro": str(e)}), 500


if __name__ == "__main__":
    # Porta dinâmica: o Render injeta a variável de ambiente PORT.
    # Localmente, sem essa variável, cai no 5000 de sempre.
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)