"""Command-line operations for this rule repository."""
import argparse,json,sys
from loon_rules import rules

def main():
    p=argparse.ArgumentParser(description=__doc__)
    group=p.add_mutually_exclusive_group()
    group.add_argument('--verify-files',action='store_true',help='本地离线校验')
    group.add_argument('--check',action='store_true',help='联网核对，但不写入本地')
    group.add_argument('--refresh',action='store_true',help='联网校验和更新本地规则；不触发推送')
    group.add_argument('--render-index',action='store_true',help='按清单重建带编号的规则索引')
    group.add_argument('--export',action='store_true',help='从已验证的规则生成各客户端格式')
    group.add_argument('--check-exports',action='store_true',help='检查客户端成品与原规则是否一致')
    p.add_argument('--adopt-ad-scope',action='store_true',help='审阅广告规则大幅变更后，一次性采用交叉核对范围，不适用于定时任务')
    args=p.parse_args()
    if args.adopt_ad_scope and not args.refresh: p.error('采纳范围变更须与 --refresh 同用')
    try:
        # Parse help before loading repository data; an installed command can
        # explain its usage even when the caller is outside a checkout.
        from loon_rules.generation import pipeline
        if args.export or args.check_exports:
            from loon_rules.exports import publish
            if args.export:
                pipeline.run(offline=True)
            changed=publish(pipeline.ROOT,check=args.check_exports)
            print('客户端格式检查通过' if args.check_exports else f'客户端格式已同步，{changed} 份文件变化')
            return 0
        if args.render_index:
            config=json.loads((pipeline.ROOT/'config/catalog.json').read_text())
            entries=pipeline.validate_declarations(config)
            (pipeline.ROOT/'docs/rules.md').write_text(pipeline.render_index(config,entries))
            if directory:=pipeline.service_directory.render(config,entries):
                (pipeline.ROOT/'docs/services.md').write_text(directory)
            if config.get('schema-version')==2:
                (pipeline.ROOT/'config/catalog.json').write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n')
            return 0
        # 默认只验证，显式 --refresh 才修改规则。
        return pipeline.run(check=args.check,adopt_ads=args.adopt_ad_scope,offline=args.verify_files or not (args.check or args.refresh))
    except (rules.Invalid,OSError,ValueError,KeyError) as error:
        print('保留上一版本：'+str(error),file=sys.stderr)
        return 2
