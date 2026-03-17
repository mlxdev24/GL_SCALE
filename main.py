# /// script
# dependencies = [
#  "pygame-ce",
#  "numpy",
#  "zengl",
# ]
# ///

import asyncio
import os
import sys
from time import perf_counter

from numpy.random import default_rng
from numpy import uint8
import pygame
from pygame import Surface
import zengl

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    os.environ["SDL_WINDOWS_DPI_AWARENESS"] = "permonitorv2"
    os.environ["SDL_WINDOWS_DPI_SCALING"] = '1'

OpenGL = True
rng = default_rng(42)


class GL_Scale:

    @staticmethod
    def load():
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 3)
        pygame.display.gl_set_attribute(
            pygame.GL_CONTEXT_PROFILE_MASK,
            pygame.GL_CONTEXT_PROFILE_CORE,
        )

    def __init__(
        self,
        window_size: tuple[int, int],
        source_size: tuple[int, int],
        *,
        filter_mode: str = "linear",
        source_order: str = "bgra",
    ):
        self.window_size = window_size
        self.source_size = source_size
        self.source_order = source_order.lower()

        self.ctx = zengl.context()

        self.texture = self.ctx.image(source_size, "rgba8unorm")

        self.output = self.ctx.image(window_size, "rgba8unorm")

        swizzle = "c" if self.source_order == "rgba" else "c.bgra"

        self.pipeline = self.ctx.pipeline(
            vertex_shader="""
                #version 330 core

                vec2 vertices[3] = vec2[](
                    vec2(-1.0, -1.0),
                    vec2( 3.0, -1.0),
                    vec2(-1.0,  3.0)
                );

                out vec2 uv;

                void main() {
                    vec2 v = vertices[gl_VertexID];
                    gl_Position = vec4(v, 0.0, 1.0);
                    uv = v * 0.5 + 0.5;
                }
            """,
            fragment_shader=f"""
                #version 330 core

                uniform sampler2D Texture;

                in vec2 uv;
                out vec4 out_color;

                void main() {{
                    vec4 c = texture(Texture, uv);
                    out_color = {swizzle};
                }}
            """,
            layout=[
                {
                    "name": "Texture",
                    "binding": 0,
                },
            ],
            resources=[
                {
                    "type": "sampler",
                    "binding": 0,
                    "image": self.texture,
                    "wrap_x": "clamp_to_edge",
                    "wrap_y": "clamp_to_edge",
                    "min_filter": filter_mode,
                    "mag_filter": filter_mode,
                },
            ],
            framebuffer=[self.output],
            topology="triangles",
            vertex_count=3,
        )

    def send(self, surface: Surface):
        if surface.get_size() != self.source_size:
            raise ValueError(
                f"Taille invalide: {surface.get_size()} != {self.source_size}"
            )

        if surface.get_bytesize() != 4:
            raise ValueError

        view = surface.get_view("0")

        self.texture.write(view)

    def render(self):
        self.output.clear()
        self.pipeline.render()
        self.output.blit()


def get_scaled_window_size():
    user32 = ctypes.windll.user32

    class RECT(ctypes.Structure):
        _fields_ = [
            ("left", wintypes.LONG),
            ("top", wintypes.LONG),
            ("width", wintypes.LONG),
            ("height", wintypes.LONG),
        ]

    hwnd = user32.GetForegroundWindow()

    client = RECT()
    ok = user32.GetClientRect(hwnd, ctypes.byref(client))
    if not ok:
        raise ctypes.WinError()

    return client.width, client.height


async def main():
    pygame.init()
    GL_Scale.load()

    window_size = (640, 360)
    win = pygame.Window(f"GL_SCALER | OPENGL_STATE: {OpenGL}", window_size, opengl=OpenGL, fullscreen_desktop=False)

    if sys.platform == "win32":
        print("Zone cliente:", get_scaled_window_size())

    scr = win.get_surface()

    src_size = (320, 180)
    surface = pygame.Surface(src_size).convert()

    scaler = GL_Scale(
        window_size=get_scaled_window_size(),
        source_size=src_size,
        filter_mode="nearest",
        source_order="bgra",
    ) if OpenGL else None

    clock = pygame.time.Clock()
    running = True
    t = 0.0

    rendered_qty = 1000
    font = pygame.font.SysFont("arial", 50)
    rendered_text = {number: font.render(f"{number}", False, "white", "green") for number in range(rendered_qty)}
    [rendered_text[number].set_colorkey("green", pygame.RLEACCEL) for number in rendered_text]

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        dt = clock.tick(0)
        t += dt

        t1 = perf_counter()
        surface.fill((0, 0, 0, 255))

        array = pygame.surfarray.pixels3d(surface)
        array[:] = rng.integers(0, 255, (*surface.get_size(), 3), dtype=uint8)
        del array

        fps = round(clock.get_fps())
        image = rendered_text[fps]
        surface.blit(image, (50, 50))

        t2 = perf_counter()
        if OpenGL:
            surface = pygame.transform.flip(surface, False, True)
            scaler.send(surface)
            scaler.render()
        else:
            pygame.transform.scale(surface, scr.get_size(), scr)

        t3 = perf_counter()

        win.flip()

        draw_time = t2 - t1
        scale_time = t3 - t2
        flip_time = perf_counter() - t3

        win.title = f"GL_SCALER | OPENGL_STATE: {OpenGL} | draw: {draw_time:.4f} | scale: {scale_time:.4f} | flip: {flip_time:.4f}"

        await asyncio.sleep(0)

    pygame.quit()


if __name__ == '__main__':
    asyncio.run(main())
