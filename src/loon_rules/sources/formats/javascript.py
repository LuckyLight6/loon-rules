"""Read static public SDK endpoints by stable purpose fields, never by minified variable names."""
import ast
import json
import re

from loon_rules.rules import Invalid
from .common import public_domain_pattern
from .structured import service_url_host


def tree(text):
    from tree_sitter import Language, Parser
    import tree_sitter_javascript
    document = Parser(Language(tree_sitter_javascript.language())).parse(text.encode('utf-8'))
    if document.root_node.has_error:
        raise Invalid('JavaScript SDK 语法变化，不能按部分结果更新')
    return document.root_node


def nodes(root):
    pending = [root]
    while pending:
        node = pending.pop()
        yield node
        pending.extend(reversed(node.named_children))


def string(node):
    if node is None or node.type != 'string':
        raise Invalid('SDK 用途地址不再是静态字符串')
    text = node.text.decode('utf-8')
    try:
        value = json.loads(text) if text.startswith('"') else ast.literal_eval(text)
    except (ValueError, SyntaxError) as error:
        raise Invalid('SDK 地址字符串无法完整读取') from error
    if not isinstance(value, str):
        raise Invalid('SDK 用途地址不是文字')
    return value


def host(node):
    row = public_domain_pattern(service_url_host(string(node)))
    if row is None:
        raise Invalid('SDK 用途地址指向共享托管范围，不能扩大认领')
    return row


def name(node):
    if node is None:
        return None
    if node.type in ('property_identifier', 'identifier'):
        return node.text.decode('utf-8')
    return string(node) if node.type == 'string' else None


def purpose_names(recipe, field):
    values = recipe.get(field)
    if (not isinstance(values, list) or not values or len(values) != len(set(values))
            or any(not isinstance(value, str) or not re.fullmatch(r'[A-Za-z_]\w*', value) for value in values)):
        raise Invalid('SDK 缺少明确且不重复的用途字段')
    return values


def environment_values(recipe, text):
    fields = purpose_names(recipe, 'fields')
    dictionary = recipe.get('dictionary-field')
    environment = recipe.get('environment')
    if any(not isinstance(value,str) or not re.fullmatch(r'[A-Za-z_]\w*',value)
           for value in (dictionary,environment)):
        raise Invalid('SDK 缺少稳定的环境字典与环境标签')
    all_nodes = list(nodes(tree(text)))
    dictionaries = [node.child_by_field_name('value') for node in all_nodes if node.type=='pair'
                    and name(node.child_by_field_name('key'))==dictionary]
    if len(dictionaries)!=1:
        raise Invalid('SDK 环境字典缺失或重复')
    selected = []
    for node in nodes(dictionaries[0]):
        if node.type!='assignment_expression':continue
        left=node.child_by_field_name('left')
        if left is None or left.type!='subscript_expression':continue
        index=left.child_by_field_name('index')
        if index is not None and index.type=='member_expression' and name(index.child_by_field_name('property'))==environment:
            selected.append(node.child_by_field_name('right'))
    if len(selected)!=1:
        raise Invalid('SDK 环境字典缺少唯一的目标环境')
    functions={'function_expression','function_declaration','arrow_function','generator_function','program'}
    def binding_scope(node):
        parent=node.parent
        lexical=parent is not None and parent.type=='lexical_declaration'
        while parent is not None:
            if parent.type in functions or lexical and parent.type=='statement_block':return parent
            parent=parent.parent
        return None
    def resolve_value(value):
        visited=set()
        while value.type=='identifier':
            identifier=name(value)
            if identifier in visited:raise Invalid('SDK 环境绑定存在循环')
            visited.add(identifier)
            candidates=[node for node in all_nodes if node.type=='variable_declarator'
                        and name(node.child_by_field_name('name'))==identifier]
            current=value.parent;found=None
            while current is not None:
                local=[candidate for candidate in candidates if binding_scope(candidate)==current]
                if len(local)>1:raise Invalid('SDK 环境变量存在重复绑定')
                if local:
                    found=local[0];break
                if current.type in functions:
                    parameters=current.child_by_field_name('parameters')
                    if parameters is not None and any(name(child)==identifier for child in parameters.named_children):
                        raise Invalid('SDK 环境变量被运行时参数覆盖')
                current=current.parent
            if found is None:raise Invalid('SDK 环境对象的绑定无法静态确认')
            if any(node.type=='assignment_expression' and name(node.child_by_field_name('left'))==identifier
                   and binding_scope(node)==binding_scope(found) for node in all_nodes):
                raise Invalid('SDK 环境对象在声明后被重新赋值')
            value=found.child_by_field_name('value')
            if value is None:raise Invalid('SDK 环境绑定没有静态默认值')
            if value.type=='object':
                for use in all_nodes:
                    if use.type!='identifier' or name(use)!=identifier or use==found.child_by_field_name('name'):
                        continue
                    scope=use.parent;bound=None
                    while scope is not None:
                        local=[candidate for candidate in candidates if binding_scope(candidate)==scope]
                        if local:
                            bound=local[0] if len(local)==1 else None
                            break
                        if scope.type in functions:
                            parameters=scope.child_by_field_name('parameters')
                            if parameters is not None and any(name(child)==identifier for child in parameters.named_children):break
                        scope=scope.parent
                    if bound!=found:continue
                    parent=use.parent
                    base=use
                    while parent is not None and parent.type in ('member_expression','subscript_expression') and parent.child_by_field_name('object')==base:
                        base=parent;parent=base.parent
                    mutation=parent is not None and (
                        parent.type in ('assignment_expression','augmented_assignment_expression') and parent.child_by_field_name('left')==base
                        or parent.type=='update_expression'
                        or parent.type=='unary_expression' and parent.text.lstrip().startswith(b'delete '))
                    alias=parent is not None and (
                        parent.type=='variable_declarator' and parent.child_by_field_name('value')==use
                        or parent.type=='assignment_expression' and parent.child_by_field_name('right')==use and use!=selected[0]
                        or parent.type in ('return_statement','pair','shorthand_property_identifier'))
                    if mutation or alias:
                        raise Invalid('SDK 环境对象在声明后被修改或交给别名')
                    if parent is not None and parent.type=='arguments':
                        arguments=[child for child in parent.named_children if child.type!='comment']
                        call=parent.parent
                        callee=call.child_by_field_name('function') if call is not None else None
                        direct=callee is not None and callee.type=='member_expression' and name(callee.child_by_field_name('object'))=='Object' and name(callee.child_by_field_name('property'))=='assign'
                        if (call!=selected[0] and not direct or len(arguments)!=2 or arguments[0].type!='object'
                                or arguments[0].named_children or arguments[1]!=use):
                            raise Invalid('SDK 环境对象传入未知调用，不能确认生产用途')
        return value
    value=selected[0]
    if value.type=='call_expression':
        arguments=value.child_by_field_name('arguments')
        args=[child for child in arguments.named_children if child.type!='comment'] if arguments is not None else []
        callee=value.child_by_field_name('function')
        if len(args)!=2 or args[0].type!='object' or args[0].named_children:
            raise Invalid('SDK 环境拷贝不是空对象与单个静态默认值')
        direct=(callee.type=='member_expression' and name(callee.child_by_field_name('object'))=='Object'
                and name(callee.child_by_field_name('property'))=='assign')
        if not direct:
            clone=resolve_value(callee)
            def shape(node):
                identifiers={}
                def visit(item):
                    if item.type=='identifier':
                        text=item.text.decode('utf-8')
                        return ('identifier',text if text in ('Object','arguments') else identifiers.setdefault(text,len(identifiers)))
                    if not item.children:return (item.type,item.text.decode('utf-8'))
                    return (item.type,tuple(visit(child) for child in item.children if child.type!='comment'))
                return visit(node)
            template='const copy=function(){return copy=Object.assign||function(target){for(var source,index=1,total=arguments.length;index<total;index++)for(var key in source=arguments[index])Object.prototype.hasOwnProperty.call(source,key)&&(target[key]=source[key]);return target},copy.apply(this,arguments)}'
            reference=next(node.child_by_field_name('value') for node in nodes(tree(template)) if node.type=='variable_declarator' and name(node.child_by_field_name('name'))=='copy')
            if shape(clone)!=shape(reference):
                raise Invalid('SDK 环境使用未知的转换函数，不能假定为 Object.assign')
        value=args[1]
    value=resolve_value(value)
    if value.type!='object':raise Invalid('SDK 环境值不再是静态对象')
    result={}
    for member in value.named_children:
        if member.type=='comment':continue
        if member.type!='pair':raise Invalid('SDK 环境对象含计算或展开字段')
        field=name(member.child_by_field_name('key'))
        if field not in fields or field in result:raise Invalid('SDK 环境对象的用途字段新增、重复或变化')
        value_node=member.child_by_field_name('value')
        host(value_node)
        result[field]=string(value_node)
    if set(result)!=set(fields):raise Invalid('SDK 环境对象的用途字段不完整')
    return result


def environment_urls(recipe,text):
    return {public_domain_pattern(service_url_host(value)) for value in environment_values(recipe,text).values()}


def method_urls(recipe, text):
    methods = purpose_names(recipe, 'methods')
    found = {method: [] for method in methods}
    for node in nodes(tree(text)):
        if node.type != 'assignment_expression':
            continue
        left = node.child_by_field_name('left')
        if left is None or left.type != 'member_expression':
            continue
        method = name(left.child_by_field_name('property'))
        if method in found:
            found[method].append(node.child_by_field_name('right'))
    result = set()
    for matches in found.values():
        if len(matches) != 1 or matches[0].type != 'function_expression':
            raise Invalid('SDK 用途构造方法缺失、重复或结构变化')
        function = matches[0]
        parameters = function.child_by_field_name('parameters')
        body = function.child_by_field_name('body')
        statements = [child for child in body.named_children if child.type != 'comment']
        if parameters.named_children or len(statements) != 1 or statements[0].type != 'return_statement':
            raise Invalid('SDK 用途构造方法含参数或额外分支')
        expressions = [child for child in statements[0].named_children if child.type != 'comment']
        if len(expressions) != 1 or expressions[0].type != 'new_expression':
            raise Invalid('SDK 用途方法不再直接返回端点构造对象')
        arguments = expressions[0].child_by_field_name('arguments')
        if arguments is None or not arguments.named_children:
            raise Invalid('SDK 端点构造缺少完整地址参数')
        for argument in arguments.named_children:
            if argument.type != 'comment':
                result.add(host(argument))
    return result


def url_literals(recipe, text):
    result = set()
    for node in nodes(tree(text)):
        if node.type == 'template_string' and node.text.startswith((b'`https://', b'`http://')):
            raise Invalid('SDK 完整地址清单出现动态模板，不能静默漏掉请求主机')
        if node.type != 'string':
            continue
        value = string(node)
        if value.startswith(('https://', 'http://')):
            result.add(host(node))
    if not result:
        raise Invalid('SDK 完整字面地址清单为空')
    return result
