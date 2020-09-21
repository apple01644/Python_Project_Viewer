import fnmatch
import os
import re
import sys
import uuid


class Module:
    def __init__(self, name: str, abs_path='', real_path='', external_module=False):
        self.imports = []
        self.name = name
        if external_module:
            self.abs_path = f'external://{name}'
            self.abs_dir = f'external://{name}'
            self.mod_path = f'external://{name}'
            self.mod_name = name[name.rfind('.') + 1:]
            self.top_dir = '__external__'
        else:
            self.abs_path = '/' + abs_path
            self.abs_dir = '/' + abs_path[:abs_path.rfind('/') + 1]
            self.mod_path = f'{abs_path[:abs_path.rfind(".")]}'.replace('/', '.')
            self.mod_name = name.replace('.py', '')
            self.mod_name = self.mod_name[self.mod_name.rfind('.') + 1:]
            if self.mod_name == '__init__':
                self.mod_name = self.abs_dir[:-1]
                self.mod_name = self.mod_name[self.mod_name.rfind('/') + 1:]

            if abs_path.find('/') == -1:
                self.top_dir = abs_path
            else:
                self.top_dir = abs_path[:abs_path.find('/')]
            self.read_source_code(real_path)

    def read_source_code(self, path):
        module_pattern = r'([\._a-zA-Z][\w\.\_]*)'
        var_name_pattern = r'([_a-zA-Z][\w\.\_]*)'
        hard_space_pattern = r'( |\\\n)+'
        soft_space_pattern = r'( |\\\n)*'
        hard_space_and_new_line_pattern = r'[ \n]+'
        soft_space_and_new_line_pattern = r'[ \n]*'

        import_pattern = rf'^(from{hard_space_pattern}{module_pattern}{hard_space_pattern})?import{hard_space_pattern}({var_name_pattern}({hard_space_pattern}as{hard_space_pattern}{var_name_pattern})?({soft_space_pattern},{soft_space_pattern}{var_name_pattern})*|\({soft_space_and_new_line_pattern}{var_name_pattern}({hard_space_pattern}as{hard_space_pattern}{var_name_pattern})?({soft_space_and_new_line_pattern},{soft_space_and_new_line_pattern}{var_name_pattern}({hard_space_and_new_line_pattern}as{hard_space_pattern}{var_name_pattern})?)*({soft_space_and_new_line_pattern},)?{soft_space_and_new_line_pattern}\)|\*)'
        from_pattern = rf'from{hard_space_pattern}{module_pattern}{hard_space_pattern}import'
        as_pattern = rf'{hard_space_pattern}as{hard_space_pattern}{var_name_pattern}{soft_space_pattern}'
        module_pattern = r'([_a-zA-Z][\w\.\_]*|\*)'

        import_regex = re.compile(import_pattern, flags=re.MULTILINE)
        from_regex = re.compile(from_pattern, flags=re.MULTILINE)
        as_regex = re.compile(as_pattern, flags=re.MULTILINE)
        module_regex = re.compile(module_pattern, flags=re.MULTILINE)

        file = open(path, 'r', encoding='utf-8').read()
        for import_match in import_regex.finditer(file):
            import_statement = str(import_match.group())

            as_statement = as_regex.search(import_statement)
            if as_statement:
                import_statement = import_statement[:as_statement.start()] + import_statement[as_statement.end():]

            from_match = from_regex.search(import_statement)
            if from_match:
                from_statement = from_match.group()
            else:
                from_statement = None
            target = import_statement[import_statement.find('import') + 6:]
            modules_statement = module_regex.findall(target)

            # from_statement
            # package_statement
            for module in modules_statement:
                self.imports.append({'from': from_statement[5:-7] if from_statement else None, 'module': module})


class ProjectAnalyzer:

    def __init__(self, target_path: str):
        self.ignore_list = set()
        self.modules = {}
        self.packages = {}
        self.import_relation = []
        self.target_path = target_path

        self.get_git_ignore()
        self.travel_files(self.target_path)

        self.make_relations()

        self.output_module = {}
        self.output = {}
        for module_id in self.modules:
            relation_data = set([str(rel['to']) for rel in self.import_relation if rel['from'] == module_id])
            module = self.modules[module_id]
            self.output_module[str(module_id)] = {'top_dir': module.top_dir,
                                                  'mod_name': module.mod_name,
                                                  'mod_path': module.mod_path,
                                                  'abs_path': module.abs_path,
                                                  'imports': relation_data}

    def add_internal_module(self, path):
        abs_path = path.replace(self.target_path, '')
        name = path[path.rfind('/') + 1:]
        module_id = uuid.uuid4()
        self.modules[module_id] = Module(name, abs_path, path)
        if name == '__init__.py':
            self.packages[abs_path[:abs_path.rfind('/')].replace('/', '.')] = module_id
        else:
            self.packages[abs_path[:-3].replace('/', '.')] = module_id
        return module_id

    def add_external_module(self, name):
        module_id = uuid.uuid4()
        self.modules[module_id] = Module(name, external_module=True)
        self.packages[name] = module_id
        return module_id

    def make_relations(self):
        external_modules = set()
        external_module_imports = {}

        for module_id in self.modules:
            mod = self.modules[module_id]
            for statement in mod.imports:
                if statement['from'] is not None:
                    if statement['from'] in self.packages:
                        self.import_relation.append({'from': module_id, 'to': self.packages[statement["from"]]})
                    else:
                        if re.match(r'\.\w+', statement['from']):
                            path = \
                                (mod.abs_path[:mod.abs_path.rfind('/')][1:] + '/' + statement['from'][1:]).replace('/',
                                                                                                                   '.')
                            if path in self.packages:
                                self.import_relation.append({'from': module_id, 'to': self.packages[path]})
                            else:
                                raise path
                        elif re.match(r'\..\w+', statement['from']):
                            top_dir = mod.abs_dir[1:-1]
                            path = top_dir[:top_dir.rfind('/') + 1].replace('/', '.') + statement['from'][2:]
                            if path in self.packages:
                                self.import_relation.append({'from': module_id, 'to': self.packages[path]})
                            else:
                                raise path
                        else:
                            explicit_path = f'{statement["from"]}.{statement["module"]}'
                            if explicit_path in self.packages:
                                self.import_relation.append({'from': module_id, 'to': self.packages[explicit_path]})
                            else:
                                if not (explicit_path in external_modules):
                                    external_modules.add(explicit_path)
                                    external_module_imports[explicit_path] = []
                                # Add relation for external package
                                external_module_imports[explicit_path].append(module_id)
        for module_name in external_modules:
            module_id = self.add_external_module(module_name)
            for importing_module_id in external_module_imports[module_name]:
                self.import_relation.append({'from': importing_module_id, 'to': module_id})

    def get_git_ignore(self):
        self.ignore_list.add('.git')
        try:
            file = open(self.target_path + '.gitignore')

            for line in file.read().splitlines():
                if len(line) > 0:
                    if line[0] != '#':
                        self.ignore_list.add(line)
        except FileNotFoundError as fe:
            pass

    def is_not_to_ignore(self, name) -> bool:
        for ignore_keyword in self.ignore_list:
            if fnmatch.fnmatch(name, ignore_keyword):
                return False
        return True

    def travel_files(self, base_path):
        for _ in os.listdir(base_path):
            rel_path = base_path.replace(self.target_path, '')
            if self.is_not_to_ignore(rel_path):
                sub_dir = base_path + f'{_}'
                if os.path.isdir(sub_dir):
                    if self.is_not_to_ignore(sub_dir) and self.is_not_to_ignore(_):
                        self.travel_files(sub_dir + '/')
                elif os.path.isfile(sub_dir):
                    if self.is_not_to_ignore(sub_dir) and self.is_not_to_ignore(_):
                        if fnmatch.fnmatch(sub_dir, '*.py'):
                            self.add_internal_module(sub_dir)


if __name__ == '__main__':
    if len(sys.argv) <= 2:
        print('Number of arguments is wrong.')
        print(f'python {sys.argv[0]} [PROJECT_DIR] [OUTPUTFILE_NAME]')
    else:
        print(f'Get file from {sys.argv[1]}')
        python_import_map = ProjectAnalyzer(sys.argv[1])
        with open(f'{sys.argv[2]}', 'w') as file:
            file.write(str(python_import_map.output_module))
