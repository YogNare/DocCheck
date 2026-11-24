from html import escape
from pathlib import Path


def write_html_report(book, path: str | Path) -> None:
    with Path(path).open("w", encoding="utf-8") as out:
        out.write("""<!doctype html>
<html lang="ru">
<meta charset="utf-8">
<title>Разбор PDF</title>
<style>
  body { max-width: 900px; margin: 2rem auto; padding: 0 1rem; font: 16px/1.5 system-ui; }
  summary { cursor: pointer; }
  .page { border: 1px solid #ccc; border-radius: 8px; padding: 1rem; margin: 1rem 0; }
  .line { margin: .4rem 0; }
  h2 { font-size: 1rem; color: #265b55; }
  small { color: #526560; }
  table { border-collapse: collapse; }
  td, th { padding: .3rem .6rem; border: 1px solid #ddd; text-align: left; }
  code { white-space: pre-wrap; }
</style>
<h1>Разбор PDF</h1>
""")

        for page in book.pages:
            out.write(
                f'<details class="page"><summary><b>Страница {page.number}</b> '
                f'<small>Верх: {len(page.header)} · Текст: {len(page.body)} · '
                f'Низ: {len(page.footer)}</small></summary>\n'
            )

            for title, indices in (
                ("Верхний колонтитул", page.header),
                ("Основной текст", page.body),
                ("Нижний колонтитул", page.footer),
            ):
                out.write(f"<h2>{title}</h2>\n")
                if not indices:
                    out.write("<small>0 строк</small>\n")

                for i in indices:
                    line = book.lines[i]
                    text = "".join(span.text for span in line.spans)
                    out.write(
                        f'<details class="line"><summary>{escape(text)} '
                        f'<small>· спанов: {len(line.spans)}</small></summary>\n'
                        f'<p>book.lines[{i}] · origin_y = {line.origin}</p>\n'
                        '<table><tr><th>Спан</th><th>Текст</th><th>Шрифт</th>'
                        '<th>Размер</th><th>Origin X</th><th>Origin Y</th></tr>\n'
                    )

                    for j, span in enumerate(line.spans):
                        x, y = span.origin
                        out.write(
                            f"<tr><td>{j}</td><td><code>{escape(repr(span.text))}</code></td>"
                            f"<td>{escape(span.font)}</td><td>{span.size}</td>"
                            f"<td>{x}</td><td>{y}</td></tr>\n"
                        )

                    out.write("</table></details>\n")

            out.write("</details>\n")

        out.write("</html>\n")