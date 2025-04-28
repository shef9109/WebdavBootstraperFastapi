from typing import Callable

from fastapi import FastAPI, Request, APIRouter
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import re
import inspect
from functools import partial
from operator import is_not
from types import ModuleType


python_controller_mask = re.compile(r'^(?P<Name>[^_]\w+)\.py$')
python_controller_class_mask = re.compile(r'^(?P<Name>[^_]\w+)Controller$')
python_action_mask = re.compile(r'^(?P<Type>(Post|Get|Put|Options|Head|Delete|Patch|))(?P<Name>[^_]\w+)Action$')
kebab_case_converter = re.compile(r'((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))')
docstring_method_mask = re.compile(r'\s+(@method)\s+(?P<Type>(get|post|put|options))')
docstring_response_model_mask = re.compile(r'@response_model\s(?P<Name>\w+)')


def to_kebab_case(func_name: str) -> str:
    return kebab_case_converter.sub(r'-\1', func_name).lower()

def get_response_model(func: Callable|type, module: ModuleType):
    if hasattr(func, 'response_model'):
        response_model = func.response_model
        if type(response_model) == str:
            module_class = getattr(module, response_model)
            return module_class
        if type(response_model) == type:
            return response_model

    docstring = func.__doc__
    if docstring is not None:
        if (docstring_match := docstring_response_model_mask.search(docstring)) is not None:
            model_name = docstring_match.group('Name')
            model_class = getattr(module, model_name, JSONResponse)
            return model_class

    return JSONResponse

def get_action_type(func: Callable, name: str) -> str:
    action_type = python_action_mask.match(name).group('Type').upper()
    if action_type != '':
        return action_type
    docstring = func.__doc__
    if docstring is None:
        return 'GET'
    if (docstring_match := docstring_method_mask.search(docstring)) is not None:
        return docstring_match.group('Type').upper()
    
    return 'GET'

def register_action(router: APIRouter, name: str, func: Callable, module: ModuleType) -> None:
    action_name = python_action_mask.match(name).group('Name')
    action_type = get_action_type(func, name)
    response_type = get_response_model(func, module)
    router.add_api_route(path=f'/{to_kebab_case(action_name)}', endpoint=func, methods=[action_type,], response_class=response_type, response_model=None)
    if action_name.lower() == 'index':
        router.add_api_route(path='/', endpoint=func, methods=[action_type,], response_class=response_type)

def create_routers(name: str, module: ModuleType, cls: type) -> list[APIRouter]:
    controller_name = python_controller_class_mask.match(name).group('Name')
    response_type = get_response_model(cls, module)
    routers = [APIRouter(
        prefix=f"/{to_kebab_case(controller_name)}" if not to_kebab_case(controller_name).startswith(
            '/') else to_kebab_case(controller_name),
        tags=[name],
        default_response_class=response_type)]
    if controller_name == 'Index':
        routers.append(APIRouter(prefix='', tags=[name], default_response_class=response_type))
    return routers

def bootstrap_controllers(app_instance: FastAPI):
    controller_files = os.listdir('app/controllers') # Список всех  файлов в дириктории
    controller_model_names = list(map(lambda f:python_controller_mask.match(f).group('Name'), filter(python_controller_mask.match, controller_files))) # Имена .py модулей из дирикторивских модулей
    modules = __import__('app.controllers', fromlist=controller_model_names) # Перечень самих пакетов модулей
    controller_modules = {controller_module:getattr(modules, controller_module) for controller_module in controller_model_names} # Словарь с именем модуля и ссылкой на него

    # Фильтрованный список контроллеров по имени и классу   
    all_controllers = filter(
        lambda name_cls: python_controller_class_mask.match(name_cls[0]),
        ((name, cls, module) for module in controller_modules.values() for name, cls in
         inspect.getmembers(module, inspect.isclass))
    )
    controller_routers = [(name, cls, module, create_routers(name, module, cls)) for name, cls, module in all_controllers]
    for name, cls, module, routers in controller_routers:
        actions = [*filter(lambda nf: python_action_mask.match(nf[0]), inspect.getmembers(cls, inspect.isfunction))]
        for router in routers:
            for action in actions:
                register_action(router, action[0], action[1], module)
            app_instance.include_router(router)


    return 1
