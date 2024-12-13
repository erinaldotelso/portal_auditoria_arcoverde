"""Add secretaria column to Resposta

Revision ID: 58074b4f88c0
Revises: 
Create Date: 2024-11-01 11:33:06.737110

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '58074b4f88c0'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('matriz_risco')
    with op.batch_alter_table('auditoria', schema=None) as batch_op:
        batch_op.drop_column('data_criacao')

    with op.batch_alter_table('comunicacao', schema=None) as batch_op:
        batch_op.alter_column('id',
               existing_type=sa.INTEGER(),
               nullable=False,
               autoincrement=True)
        batch_op.alter_column('data',
               existing_type=sa.NUMERIC(),
               type_=sa.Date(),
               nullable=False)
        batch_op.alter_column('mensagem',
               existing_type=sa.TEXT(),
               nullable=False)
        batch_op.alter_column('data_criacao',
               existing_type=sa.NUMERIC(),
               type_=sa.DateTime(),
               existing_nullable=True)
        batch_op.alter_column('data_atualizacao',
               existing_type=sa.NUMERIC(),
               type_=sa.DateTime(),
               existing_nullable=True)

    with op.batch_alter_table('matriz_planejamento', schema=None) as batch_op:
        batch_op.alter_column('exercicio',
               existing_type=sa.VARCHAR(length=10),
               type_=sa.String(length=4),
               existing_nullable=False)

    with op.batch_alter_table('relatorio', schema=None) as batch_op:
        batch_op.alter_column('data_criacao',
               existing_type=sa.DATETIME(),
               nullable=True)
        batch_op.alter_column('data_atualizacao',
               existing_type=sa.DATETIME(),
               nullable=True)

    with op.batch_alter_table('respostas', schema=None) as batch_op:
        batch_op.add_column(sa.Column('secretaria', sa.String(length=100), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('respostas', schema=None) as batch_op:
        batch_op.drop_column('secretaria')

    with op.batch_alter_table('relatorio', schema=None) as batch_op:
        batch_op.alter_column('data_atualizacao',
               existing_type=sa.DATETIME(),
               nullable=False)
        batch_op.alter_column('data_criacao',
               existing_type=sa.DATETIME(),
               nullable=False)

    with op.batch_alter_table('matriz_planejamento', schema=None) as batch_op:
        batch_op.alter_column('exercicio',
               existing_type=sa.String(length=4),
               type_=sa.VARCHAR(length=10),
               existing_nullable=False)

    with op.batch_alter_table('comunicacao', schema=None) as batch_op:
        batch_op.alter_column('data_atualizacao',
               existing_type=sa.DateTime(),
               type_=sa.NUMERIC(),
               existing_nullable=True)
        batch_op.alter_column('data_criacao',
               existing_type=sa.DateTime(),
               type_=sa.NUMERIC(),
               existing_nullable=True)
        batch_op.alter_column('mensagem',
               existing_type=sa.TEXT(),
               nullable=True)
        batch_op.alter_column('data',
               existing_type=sa.Date(),
               type_=sa.NUMERIC(),
               nullable=True)
        batch_op.alter_column('id',
               existing_type=sa.INTEGER(),
               nullable=True,
               autoincrement=True)

    with op.batch_alter_table('auditoria', schema=None) as batch_op:
        batch_op.add_column(sa.Column('data_criacao', sa.DATETIME(), nullable=True))

    op.create_table('matriz_risco',
    sa.Column('id', sa.INTEGER(), nullable=False),
    sa.Column('identificacao', sa.VARCHAR(length=255), nullable=False),
    sa.Column('probabilidade', sa.VARCHAR(length=50), nullable=True),
    sa.Column('impacto', sa.VARCHAR(length=50), nullable=True),
    sa.Column('categoria', sa.VARCHAR(length=50), nullable=True),
    sa.Column('proprietario', sa.VARCHAR(length=255), nullable=False),
    sa.Column('plano_acao', sa.VARCHAR(length=255), nullable=True),
    sa.Column('prazo', sa.DATE(), nullable=False),
    sa.Column('status', sa.VARCHAR(length=50), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###
