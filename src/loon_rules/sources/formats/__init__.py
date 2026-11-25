"""Dispatch public input formats. Each reader returns rule rows, never policy names."""
from loon_rules import domains as domain_scope
from loon_rules.rules import Invalid
from . import api, contextual, documents, feeds, networks, python_regions, regions, structured, tables


def security_program_rows(recipe, text):
    # The audit module also imports format helpers, so load it after dispatch setup.
    from loon_rules.sources.security_programs import extract
    return extract(recipe, text)


READERS = {
    'annotated-domains': feeds.parse_annotated_domains,
    'api-discovery': structured.api_discovery,
    'article-domain-list': documents.parse_article_domain_list,
    'azure-cloud-metadata': api.parse_azure_cloud_metadata,
    'brand-region-links': documents.parse_brand_region_links,
    'brand-domain-list': structured.brand_domain_list,
    'c-function-url': api.c_function_url,
    'code-api-endpoints': api.parse_code_api_endpoints,
    'csp-origins': documents.csp_origins,
    'curl-api-endpoints': api.parse_curl_api_endpoints,
    'destination-table': tables.parse_destination_table,
    'domain-column-table': tables.domain_column_table,
    'domain-scope-list': feeds.domain_scope_list,
    'geosite-domain-list': feeds.geosite_domain_list,
    'derp-map': structured.derp_map,
    'endpoint-network-sets': networks.parse_endpoint_network_sets,
    'endpoint-sets': tables.parse_endpoint_sets,
    'go-host-switch': api.go_host_switch,
    'exclusive-purpose-table': tables.exclusive_purpose_table,
    'help-center-domains': documents.parse_help_center_domains,
    'host-table': tables.parse_host_table,
    'host-purpose-list': documents.host_purpose_list,
    'http-provider-lists': feeds.parse_http_provider_lists,
    'https-hosts': feeds.parse_https_hosts,
    'ip-prefix-json': networks.parse_ip_prefix_json,
    'json-service-urls': structured.json_service_urls,
    'labelled-networks': networks.parse_labelled_networks,
    'labelled-url-pairs': contextual.labelled_url_pairs,
    'literal-object-urls': api.literal_object_urls,
    'mail-autoconfig': feeds.parse_mail_autoconfig,
    'markdown-purpose-endpoints': contextual.markdown_purpose_endpoints,
    'named-hosts': feeds.parse_named_hosts,
    'nested-purpose-domains': contextual.nested_purpose_domains,
    'next-service-urls': structured.next_service_urls,
    'openid-discovery': feeds.parse_openid_discovery,
    'plist-service-fields': structured.plist_service_fields,
    'product-domain-statements': documents.parse_product_domain_statements,
    'product-entrypoints': documents.parse_product_entrypoints,
    'product-role-links': documents.parse_product_role_links,
    'purpose-domain-lists': documents.parse_purpose_domain_lists,
    'purpose-domain-table': contextual.purpose_domain_table,
    'purpose-host-table': tables.parse_purpose_host_table,
    'purpose-url-table': tables.purpose_url_table,
    'python-sdk-endpoints': api.parse_python_sdk_endpoints,
    'python-regional-hosts': python_regions.read,
    'qt-host-predicate': api.qt_host_predicate,
    'region-endpoint-table': regions.extract,
    'rdap-autnum': networks.rdap_autnum,
    'rdap-entity-autnums': networks.rdap_entity_autnums,
    'section-network-blocks': networks.section_network_blocks,
    'rules': feeds.parse_rules,
    'sdk-client-endpoints': api.parse_sdk_client_endpoints,
    'section-media-networks': networks.parse_section_media_networks,
    'section-code-domains': documents.section_code_domains,
    'service-default-host': api.parse_service_default_host,
    'service-address-table': networks.service_address_table,
    'service-domain-table': tables.parse_service_domain_table,
    'service-domain-groups': structured.service_domain_groups,
    'security-program-domains': security_program_rows,
    'site-identity': documents.parse_site_identity,
    'site-resource-hosts': documents.site_resource_hosts,
    'vim-config-defaults': api.parse_vim_config_defaults,
    'windows-purpose': tables.parse_windows_purpose,
}

def extract_rows(recipe, text, *, shared_hosts=()):
    form = recipe['format']
    if form=='json-document':
        nested=dict(recipe['document'])
        if 'source' in recipe:
            if 'source' in nested and nested['source']!=recipe['source']:raise Invalid('资料正文字段不能改换来源身份')
            nested['source']=recipe['source']
        return extract_rows(nested,structured.document_body(recipe,text),shared_hosts=shared_hosts)
    if form not in READERS:
        raise Invalid('未知端点资料格式：' + form)
    result=set(READERS[form](recipe,text))
    source_alias=form=='site-identity' and recipe.get('include-source-alias')
    strict_scope = (source_alias or form == 'python-sdk-endpoints' and 'dictionary-host-fields' in recipe
                    or form in ('domain-scope-list', 'geosite-domain-list', 'site-resource-hosts',
                                'qt-host-predicate', 'next-service-urls', 'literal-object-urls',
                                'security-program-domains', 'nested-purpose-domains', 'service-domain-groups',
                                'json-service-urls', 'plist-service-fields', 'purpose-domain-table',
                                'python-regional-hosts'))
    if (strict_scope or form in ('json-service-urls','plist-service-fields','section-code-domains','purpose-domain-lists',
                 'go-host-switch','c-function-url','csp-origins','domain-column-table','product-role-links','purpose-host-table')
            or form=='endpoint-sets' and recipe.get('all-hosts')
            or form=='product-domain-statements' and recipe.get('code-only')):
        before=result
        hosts = shared_hosts
        if form == 'service-domain-groups':
            platforms = structured.service_namespace_roots(recipe)
            hosts = [host for host in shared_hosts if not any(
                domain_scope.fixed_tail(host) == root or domain_scope.fixed_tail(host).endswith('.' + root)
                for root in platforms)]
        result=set(domain_scope.exclude_shared_scopes(result,hosts))
        if strict_scope and result!=before:
            raise Invalid('完整产品范围包含共享主机，不能静默忽略或认领')
        if not result:raise Invalid('服务 URL 仅指向共用请求入口，不能按文件路径认领整个主机')
    return result
