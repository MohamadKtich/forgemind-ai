"""ForgeMind AI initial schema baseline."""
from alembic import op
from backend.app.db import Base
import backend.app.models  # noqa: F401
revision = "20260724_0001"
down_revision = None
branch_labels = None
depends_on = None
def upgrade():
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)
def downgrade():
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
