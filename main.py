import io
import fitz  # PyMuPDF
import streamlit as st
from PIL import Image


def compress_pdf_safe(input_bytes: bytes, quality: int = 40) -> bytes:
    """
    Compresses the PDF by correctly extracting images using their proper cross-reference index (xref),
    downscaling them via Pillow, and saving the optimized file.
    """
    doc = fitz.open(stream=input_bytes, filetype="pdf")

    for page in doc:
        # get_images() returns a list of tuples; the 1st element [0] is the true xref ID
        for img_info in page.get_images(full=True):
            xref = img_info[0]

            try:
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]

                # Load image into Pillow
                pil_img = Image.open(io.BytesIO(image_bytes))

                # Convert color spaces safely to prevent JPEG saving errors
                if pil_img.mode in ("RGBA", "P"):
                    pil_img = pil_img.convert("RGB")

                # Compress the image in memory
                compressed_img_io = io.BytesIO()
                pil_img.save(compressed_img_io, format="JPEG", quality=quality, optimize=True)

                # Safely update the PDF object link
                page.replace_image(xref, stream=compressed_img_io.getvalue())
            except Exception:
                continue

    output_buffer = io.BytesIO()
    # Save using standard, built-in optimization tools
    doc.save(
        output_buffer,
        garbage=4,
        deflate=True,
        clean=True
    )
    doc.close()
    return output_buffer.getvalue()


# --- Streamlit Frontend ---
st.set_page_config(page_title="Deep PDF Compressor", page_icon="📄")
st.title("⚡ Deep PDF Compressor")
st.write("Drastically shrink PDF sizes by optimizing internal images.")

uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"])

if uploaded_file is not None:
    file_bytes = uploaded_file.read()
    initial_size = len(file_bytes) / 1024  # KB
    st.info(f"Original Size: **{initial_size:.2f} KB**")

    # Slider to change image resolution quality
    quality_setting = st.slider("Image Quality (Lower = Smaller File)", min_value=10, max_value=90, value=40)

    if st.button("🚀 Compress PDF Now"):
        with st.spinner("Deep compressing images..."):
            try:
                compressed_bytes = compress_pdf_safe(file_bytes, quality=quality_setting)
                final_size = len(compressed_bytes) / 1024  # KB

                savings = initial_size - final_size
                percent_saved = (savings / initial_size) * 100 if initial_size > 0 else 0

                if final_size >= initial_size:
                    st.warning("This PDF is already fully optimized!")
                else:
                    st.success(f"Compressed Size: **{final_size:.2f} KB** (Saved **{percent_saved:.1f}%**)")

                    st.download_button(
                        label="📥 Download Compressed PDF",
                        data=compressed_bytes,
                        file_name=f"compressed_{uploaded_file.name}",
                        mime="application/pdf"
                    )
            except Exception as e:
                st.error(f"Compression failed: {str(e)}")