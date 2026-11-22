"""Project a routing check onto exactly the choices that can change its result."""
from itertools import product


def view_graph(config, entries):
    keys=tuple(config['views'])
    members={key:set(entries[key]['members']) for key in keys}
    return keys,{key:{other for other in keys if other!=key and members[key]&members[other]} for key in keys}


def view_selections(config, entries, *, maximal=False):
    keys,graph=view_graph(config,entries);remaining=set(keys);components=[]
    for key in keys:
        if key not in remaining:continue
        component={key};pending=[key];remaining.remove(key)
        while pending:
            added=graph[pending.pop()]&remaining
            remaining.difference_update(added);component.update(added);pending.extend(added)
        local=[key for key in keys if key in component]
        choices=[()]
        for key in local:
            choices.extend(selected+(key,) for selected in choices.copy() if not graph[key]&set(selected))
        if maximal:
            choices=[selected for selected in choices
                     if all(key in selected or graph[key]&set(selected) for key in local)]
        components.append(choices)
    for groups in product(*components):
        selected={key for group in groups for key in group}
        yield tuple(key for key in keys if key in selected)


class ChoiceModel:
    def __init__(self, config, entries, bits):
        self.bits=bits
        self.extras=tuple(key for key in config.get('optional',()) if entries[key].get('domain-remainder'))
        views,graph=view_graph(config,entries)
        self.keys=(*views,*self.extras)
        self.variables={key:1<<i for i,key in enumerate(self.keys)}
        self.conflicts={self.variables[key]:sum(self.variables[other] for other in graph.get(key,()))
                        for key in self.keys}
        self.members={self.variables[key]:sum(bits[member] for member in entries[key]['members'])
                      for key in views}
        self.rule_bits={self.variables[key]:bits[key] for key in self.keys}
        self.base=sum(bits[key] for key in config['detailed']+config['general'])
        self.controls={bit:0 for bit in bits.values()}
        for key in self.keys:self.controls[bits[key]]|=self.variables[key]
        for key in views:
            for member in entries[key]['members']:self.controls[bits[member]]|=self.variables[key]
        self._counts={}
        self._scenarios={}

    def _count(self, available):
        if available in self._counts:return self._counts[available]
        if not available:return 1
        linked=[bit for bit,neighbors in self.conflicts.items() if available&bit and available&neighbors]
        if not linked:return 1<<available.bit_count()
        bit=max(linked,key=lambda bit:(available&self.conflicts[bit]).bit_count())
        result=self._count(available&~bit)+self._count(available&~(bit|self.conflicts[bit]))
        self._counts[available]=result
        return result

    def count(self):
        return self._count((1<<len(self.keys))-1)

    def relevant(self, rule_bits):
        result=0
        while rule_bits:
            bit=rule_bits&-rule_bits;rule_bits^=bit
            result|=self.controls[bit]
        return result

    def _selections(self, variables):
        if variables in self._scenarios:return self._scenarios[variables]
        pending=variables
        choices=[0]
        while pending:
            bit=pending&-pending;pending^=bit
            choices.extend(chosen|bit for chosen in choices.copy() if not chosen&self.conflicts[bit])
        result=[]
        for chosen in choices:
            selected=self.base;pending=chosen
            while pending:
                bit=pending&-pending;pending^=bit
                selected&=~self.members.get(bit,0)
                selected|=self.rule_bits[bit]
            result.append(selected)
        self._scenarios[variables]=tuple(result)
        return self._scenarios[variables]

    def selections(self, rule_bits):
        # Every local choice extends to a legal full choice by leaving unrelated views off.
        # No omitted variable can change the activity of these rules.
        return self._selections(self.relevant(rule_bits))

    def together(self, rule_bits):
        return any(selected&rule_bits==rule_bits for selected in self.selections(rule_bits))
