import pygame
from pygame import Surface
import zengl


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


def main():
    pygame.init()
    GL_Scale.load()

    # window_size = (1280, 720)
    window_size = (3840, 2160)
    win = pygame.Window("OpenGL", window_size, opengl=True)
    scr = win.get_surface()

    src_size = (320, 180)
    surface = pygame.Surface(src_size, flags=pygame.SRCALPHA, depth=32).convert_alpha()

    scaler = GL_Scale(
        window_size=window_size,
        source_size=src_size,
        filter_mode="nearest",
        source_order="bgra",
    )

    clock = pygame.time.Clock()
    running = True
    t = 0.0

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        t += 0.016

        surface.fill((20, 20, 30, 255))
        pygame.draw.circle(
            surface,
            (255, 140, 0, 255),
            (int(160 + 80 * __import__("math").sin(t)), 90),
            30,
        )
        pygame.draw.rect(surface, (80, 200, 255, 255), (20, 20, 80, 40))

        scaler.send(surface)
        scaler.render()

        win.title = f"{clock.get_fps():.1f}"
        win.flip()
        clock.tick(0)

    pygame.quit()


if __name__ == '__main__':
    main()