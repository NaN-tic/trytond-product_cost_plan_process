from datetime import datetime

from trytond.model import ModelView, fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval, Bool
from trytond.transaction import Transaction
from trytond.wizard import Wizard, StateView, StateAction, Button
from trytond.i18n import gettext
from trytond.exceptions import UserWarning, UserError

__all__ = ['Plan', 'CreateProcessStart', 'CreateProcess']


class Plan(metaclass=PoolMeta):
    __name__ = 'product.cost.plan'

    process = fields.Many2One('production.process', 'Process',
        domain=[
            ('uom', '=', Eval('uom'))
            ],
        depends=['uom'])

    @classmethod
    def __setup__(cls):
        super(Plan, cls).__setup__()
        cls.product.domain += [('producible', '=', True)]
        cls.bom.states.update({
                'readonly': Bool(Eval('process')),
                })
        cls.bom.depends.add('process')
        cls.route.states.update({
                'readonly': Bool(Eval('process')),
                })
        cls.route.depends.add('process')

    @fields.depends('process', methods=['on_change_process'])
    def on_change_product(self):
        self.process = None
        self.bom = None
        self.boms = None
        self.route = None
        super(Plan, self).on_change_product()
        if self.product and self.product.boms:
            for product_bom in self.product.boms:
                if product_bom.process:
                    self.process = product_bom.process
                    self.on_change_process()
                    break

    @fields.depends('process', 'bom', 'boms', methods=['on_change_with_boms'])
    def on_change_process(self):
        BomLine = Pool().get('product.cost.plan.bom_line')
        to_delete = []
        if self.process:
            if self.boms:
                to_delete = self.boms
            self.bom = self.process.bom
            self.boms = []
            self.route = self.process.route
            boms = []
            for i, x in self.on_change_with_boms().get('add', []):
                boms.append(BomLine(product=x['product'], bom=x['bom']))
            self.boms = boms

        if to_delete:
            with Transaction().new_transaction(autocommit=True, readonly=False):
                BomLine.delete(to_delete)

    def create_process(self, name):
        pool = Pool()
        Process = pool.get('production.process')
        Step = pool.get('production.process.step')
        Warning = pool.get('res.user.warning')

        if not self.product:
            raise UserError(gettext('product_cost_plan.lacks_the_product',
                    cost_plan=self.rec_name))
        key = 'process_already_exists%s' % self.id
        if self.process and Warning.check(key):
            raise UserWarning(key,
                gettext('product_cost_plan_process.msg_process_already_exists',
                    cost_plan=self.rec_name))

        bom = self.bom
        if not bom:
            bom = self.create_bom(name)

        route = self.route
        if not route:
            route = self.create_route(name)

        process = Process(name=name, uom=self.uom)
        process.bom = bom
        process.route = route
        process.save()
        self.process = process
        self.save()
        step_name = Process.fields_get(['steps'])['steps']['string']
        step = Step(name=step_name, process=process)
        step.inputs = bom.inputs
        step.outputs = bom.outputs
        step.operations = route.operations
        step.save()

        for product_bom in self.product.boms:
            if product_bom.bom == bom and product_bom.route == route:
                product_bom.process = process
                product_bom.save()
                break
        else:
            raise UserError(gettext(
                    'product_cost_plan_process.msg_cannot_assign_process_to_product',
                    process=self.rec_name, product=self.product.rec_name))
        return process

    @classmethod
    def copy(cls, plans, default=None):
        if default is None:
            default = {}
        else:
            default = default.copy()
        default['process'] = None
        return super(Plan, cls).copy(plans, default=default)


class CreateProcessStart(ModelView):
    'Create Process Start'
    __name__ = 'product.cost.plan.create_process.start'

    name = fields.Char('Name', required=True)


class CreateProcess(Wizard):
    'Create Process'
    __name__ = 'product.cost.plan.create_process'

    start = StateView('product.cost.plan.create_process.start',
        'product_cost_plan_process.create_process_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Ok', 'process', 'tryton-ok', True),
            ])
    process = StateAction('production_process.act_production_process')

    def default_start(self, fields):
        if self.record:
            now = datetime.now()
            return {
                'name': '%s (%s)' % (self.record.rec_name or '', now.strftime('%d/%m/%Y')),
                }
        return {}

    def do_process(self, action):
        if self.record:
            process = self.record.create_process(self.start.name)
            data = {
                'res_id': [process.id],
                }
            action['views'].reverse()
            return action, data
        else:
            return 'end'
