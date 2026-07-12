from __future__ import annotations

import base64
from dataclasses import dataclass
from io import BytesIO
from typing import TYPE_CHECKING

import qrcode
from PIL import Image, ImageDraw

if TYPE_CHECKING:
    from collections.abc import Sequence


def _escape_xml_attr(value: str) -> str:
    """Escape a string so it can be safely used in an XML attribute."""
    return (
        value.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")
    )


@dataclass(frozen=True)
class QRStyle:
    """Visual styling parameters for a QR code."""

    fill_color: str
    back_color: str
    module_round: float
    box_size: int
    border: int


class QRCodeBuilder:
    """Build a configured qrcode.QRCode instance from raw data."""

    def __init__(self, box_size: int, border: int) -> None:
        self.box_size = box_size
        self.border = border

    def build(self, data: str) -> qrcode.QRCode:
        """Create and configure a QR code instance."""
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=self.box_size,
            border=self.border,
        )
        qr.add_data(data)
        qr.make(fit=True)
        return qr


class PNGRenderer:
    """Render a QR code as a styled base64-encoded PNG."""

    def __init__(self, style: QRStyle, *, render_scale: int = 3) -> None:
        self.style = style
        self.render_scale = render_scale

    def render(self, qr: qrcode.QRCode) -> str:
        """Generate a styled PNG QR code and return it as a base64 string."""
        modules: Sequence[Sequence[bool]] = qr.modules

        module_size = self.style.box_size * self.render_scale
        border_px = self.style.border * module_size
        size = len(modules) * module_size + 2 * border_px

        img = Image.new("RGB", (size, size), self.style.back_color)
        draw = ImageDraw.Draw(img)

        padding = 1
        radius = int(module_size * self.style.module_round)

        for row_index, row in enumerate(modules):
            for col_index, module in enumerate(row):
                if module:
                    x = border_px + col_index * module_size
                    y = border_px + row_index * module_size
                    draw.rounded_rectangle(
                        [
                            x + padding,
                            y + padding,
                            x + module_size - padding,
                            y + module_size - padding,
                        ],
                        radius=radius,
                        fill=self.style.fill_color,
                    )

        count = len(modules)
        final_size = count * self.style.box_size + 2 * self.style.border * self.style.box_size
        img = img.resize((final_size, final_size), Image.Resampling.LANCZOS)

        buffer = BytesIO()
        img.save(buffer, format="PNG", optimize=True)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")


class SVGRenderer:
    """Render a QR code as styled SVG markup."""

    def __init__(self, style: QRStyle) -> None:
        self.style = style

    def render(self, qr: qrcode.QRCode) -> str:
        """Generate a styled SVG QR code and return the SVG markup."""
        modules: Sequence[Sequence[bool]] = qr.modules
        count = len(modules)
        size = count * self.style.box_size + 2 * self.style.border * self.style.box_size

        safe_fill = _escape_xml_attr(self.style.fill_color)
        safe_back = _escape_xml_attr(self.style.back_color)

        svg_parts: list[str] = [
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {size} {size}" width="{size}" height="{size}">',
            f'<rect width="100%" height="100%" fill="{safe_back}"/>',
        ]

        for row_index, row in enumerate(modules):
            for col_index, module in enumerate(row):
                if module:
                    x = (col_index + self.style.border) * self.style.box_size
                    y = (row_index + self.style.border) * self.style.box_size
                    svg_parts.append(
                        f'<rect x="{x}" y="{y}" width="{self.style.box_size}" '
                        f'height="{self.style.box_size}" '
                        f'rx="{self.style.box_size * self.style.module_round}" '
                        f'fill="{safe_fill}"/>'
                    )

        svg_parts.append("</svg>")
        return "".join(svg_parts)


class StyledQRGenerator:
    """High-level service for generating styled QR codes in PNG or SVG formats."""

    def __init__(self, style: QRStyle) -> None:
        self.style = style
        self._builder = QRCodeBuilder(box_size=style.box_size, border=style.border)
        self._png_renderer = PNGRenderer(style)
        self._svg_renderer = SVGRenderer(style)

    def generate_png(self, data: str) -> str:
        """Generate a styled PNG QR code and return it as a base64 string."""
        qr = self._builder.build(data)
        return self._png_renderer.render(qr)

    def generate_svg(self, data: str) -> str:
        """Generate a styled SVG QR code and return the SVG markup."""
        qr = self._builder.build(data)
        return self._svg_renderer.render(qr)
