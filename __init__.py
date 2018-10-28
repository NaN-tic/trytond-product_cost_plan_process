# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from . import plan


def register():
    Pool.register(
        plan.Plan,
        plan.CreateProcessStart,
        module='product_cost_plan_process', type_='model')
    Pool.register(
        plan.CreateProcess,
        module='product_cost_plan_process', type_='wizard')
