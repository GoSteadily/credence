#!/usr/bin/env python3
from pathlib import Path
import shutil
import textwrap

from jinja2 import Environment
from jinja2 import FileSystemLoader
from markupsafe import Markup
import pygments.formatters.html
import pygments.lexers.python

import pdoc.render

here = Path(__file__).parent

if __name__ == "__main__":
    credence = here / ".." / "src" / "credence" / "__init__.py"

    # Render main docs
    pdoc.render.configure(
        edit_url_map={
            "credence": "https://github.com/GoSteadily/credence/blob/main/src/credence/",
        },
        show_source=False,
        # favicon="/favicon.svg",
        # logo="/logo.svg",
        logo_link="https://github.com/GoSteadily/credence",
    )
    pdoc.pdoc(
        credence,
        "!credence.role",
        output_directory=here / "docs",
    )

    # Add sitemap.xml
    with (here / "docs" / "sitemap.xml").open("w", newline="\n") as f:
        f.write(
            textwrap.dedent(
                """
        <?xml version="1.0" encoding="utf-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
           xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
           xsi:schemaLocation="http://www.sitemaps.org/schemas/sitemap/0.9 http://www.sitemaps.org/schemas/sitemap/0.9/sitemap.xsd">
        """
            ).strip()
        )
        for file in here.glob("**/*.html"):
            if file.name.startswith("_"):
                continue
            filename = str(file.relative_to(here).as_posix()).replace("index.html", "")
            f.write(
                f"""\n<url><loc>https://github.com/GoSteadily/credence/{filename}</loc></url>""")
        f.write("""\n</urlset>""")
