# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from .plan import *


def register():
    Pool.register(
        Plan,
        CreateProcessStart,
        module='product_cost_plan_process', type_='model')
    Pool.register(
        CreateProcess,
        module='product_cost_plan_process', type_='wizard')
