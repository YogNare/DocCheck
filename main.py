import pymupdf

doc = pymupdf.open("samples/simple3.pdf")

page = doc.load_page(0)
blocks = page.get_text("dict")

print(blocks)