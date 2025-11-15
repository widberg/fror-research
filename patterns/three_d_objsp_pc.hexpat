import fror;

struct VertexBuffer<auto S> {
    Vec3f vertices[S];
    Vec2U16Float uvs[S];
};

VertexBuffer<602> vertex_buffer @ 0x0;
