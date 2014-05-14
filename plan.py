from trytond.model import ModelView, fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval, Bool
from trytond.transaction import Transaction
from trytond.wizard import Wizard, StateView, StateAction, Button

__all__ = ['Plan', 'CreateProcessStart', 'CreateProcess']
__metaclass__ = PoolMeta


class Plan:
    __name__ = 'product.cost.plan'

    process = fields.Many2One('production.process', 'Process',
        domain=[
            ('uom', '=', Eval('uom'))
            ],
        depends=['uom'], on_change=[])

    @classmethod
    def __setup__(cls):
        super(Plan, cls).__setup__()
        cls.bom.states.update({
                'readonly': Bool(Eval('process')),
                })
        cls.bom.depends.append('process')
        cls.route.states.update({
                'readonly': Bool(Eval('process')),
                })
        cls.route.depends.append('process')
        cls._error_messages.update({
                'process_already_exists': ('A process already exists for cost '
                    'plan "%s".'),
                })

    def on_change_process(self):
        res = {}
        if self.process:
            self.bom = self.process.bom
            res['bom'] = self.bom.id
            self.route = self.process.route
            res['route'] = self.route.id
        return res

    def create_process(self, name):
        pool = Pool()
        Process = pool.get('production.process')
        Step = pool.get('production.process.step')
        if self.process:
            self.raise_user_error('process_already_exists', self.rec_name)

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

        return process


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
        CostPlan = Pool().get('product.cost.plan')
        plan = CostPlan(Transaction().context.get('active_id'))
        return {
            'name': plan.product.rec_name,
            }

    def do_process(self, action):
        pool = Pool()
        CostPlan = pool.get('product.cost.plan')
        plan = CostPlan(Transaction().context.get('active_id'))
        process = plan.create_process(self.start.name)
        data = {
            'res_id': [process.id],
            }
        action['views'].reverse()
        return action, data
