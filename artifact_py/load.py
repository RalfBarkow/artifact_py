# artifact_py: the design documentation tool made for everyone.
#
# Copyright (C) 2019 Rett Berg <github.com/vitiral>
#
# The source code is Licensed under either of
#
# * Apache License, Version 2.0, ([LICENSE-APACHE](LICENSE-APACHE) or
#   http://www.apache.org/licenses/LICENSE-2.0)
# * MIT license ([LICENSE-MIT](LICENSE-MIT) or
#   http://opensource.org/licenses/MIT)
#
# at your option.
#
# Unless you explicitly state otherwise, any contribution intentionally submitted
# for inclusion in the work by you, as defined in the Apache-2.0 license, shall
# be dual licensed as above, without any additional terms or conditions.
from __future__ import unicode_literals
import copy

import six
import anchor_txt
import networkx as nx

from . import settings
from . import project
from . import artifact
from . import name
from . import code


def from_root_file(root_file):
    root_section = anchor_txt.Section.from_md_path(root_file)
    p_settings = settings.Settings.from_dict(
        root_section.attributes.get('artifact', {}), root_file)

    impls = code.find_impls(p_settings)

    project_sections = load_project_sections(
        sections=root_section.sections,
        file_=root_file,
        impls=impls,
    )

    artifacts_builder = load_artifacts_builder(project_sections)
    return project.Project(
        settings=p_settings,
        artifacts=[b.build() for b in artifacts_builder.builders],
        contents=root_section.contents,
        sections=project_sections,
    )


def load_project_sections(sections, file_, impls):
    """Load artifacts from the sections.
    """

    # project sections can either be:
    # - a raw section
    # - an ArtifactBuilder, which contains a section
    project_sections = []

    for section in sections:
        try:
            art_name = name.Name.from_str(section.header.anchor)
        except ValueError:
            project_sections.append(section)
            continue

        impl = impls.get(art_name)
        if not impl:
            impl = code.ImplCode.new()

        art_im = artifact.ArtifactBuilder.from_attributes(
            attributes=section.attributes,
            name=art_name,
            file_=file_,
            impl=impl,
            section=section,
        )

        project_sections.append(art_im)

    return project_sections


def load_artifacts_builder(project_sections):
    graph = nx.DiGraph()

    builders = [
        s for s in project_sections if isinstance(s, artifact.ArtifactBuilder)
    ]

    # create the graph
    for art in builders:
        graph.add_node(art.name)

        for part in art.partof:
            graph.add_edge(part, art.name)

    for art in builders:
        art.set_parts(set(graph.neighbors(art.name)))

    return artifact.ArtifactsBuilder(builders=builders, graph=graph)


def ratio(value, count):
    """compute ratio but ignore count=0"""
    if count == 0:
        return 0.0
    else:
        return value / count


def determine_completed(artifacts_builder, code_impls):
    builder_map = artifacts_builder.builder_map
    graph = artifacts_builder.graph

    sorted_graph = nx.algorithms.dag.topological_sort(graph)
    sorted_graph = list(sorted_graph)

    specified = {}
    tested = {}

    for name in reversed(sorted_graph):
        builder = builder_map.get(name)
        (count_spc, value_spc, count_tst,
         value_tst) = builder.impl.to_statistics(code_impls)

        if name.is_tst():
            for name in graph.neighbors():
                value_spc += specified[name]
                count_spc += 1
            value_tst = value_spc
            count_tst = count_spc
        else:
            for neighbor in graph.neighbors():
                value_tst += tested[neighbor]
                count_tst += 1

                if not neighbor.is_tst():
                    value_spc += specified[neighbor]
                    count_spc += 1

        tested[name] = ratio(value_tst, count_tst)
        specified[name] = ratio(value_spc, count_spc)

    # debug_assert_eq!(impls.len(), implemented.len());
    # debug_assert_eq!(impls.len(), tested.len());
    # let out: IndexMap<Name, Completed> = implemented
    #     .iter()
    #     .map(|(id, spc)| {
    #         // throw away digits after 1000 significant digit
    #         // (note: only at end of all calculations!)
    #         let compl = Completed {
    #             spc: round_ratio(*spc),
    #             tst: round_ratio(tested[id]),
    #         };
    #         (graphs.lookup_name[id].clone(), compl)
    #     })
    #     .collect();
    # debug_assert_eq!(impls.len(), out.len());
    # out
