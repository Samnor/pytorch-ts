import pytest
from itertools import chain, combinations


import torch
import torch.nn as nn

from pts.modules import FeatureEmbedder, FeatureAssembler

@pytest.mark.parametrize(
    "config",
    (
        lambda N, T: [
            # single static feature
            dict(
                shape=(N, 1),
                kwargs=dict(cardinalities=[50], embedding_dims=[10]),
            ),
            # single dynamic feature
            dict(
                shape=(N, T, 1),
                kwargs=dict(cardinalities=[2], embedding_dims=[10]),
            ),
            # multiple static features
            dict(
                shape=(N, 4),
                kwargs=dict(
                    cardinalities=[50, 50, 50, 50],
                    embedding_dims=[10, 20, 30, 40],
                ),
            ),
            # multiple dynamic features
            dict(
                shape=(N, T, 3),
                kwargs=dict(
                    cardinalities=[30, 30, 30], embedding_dims=[10, 20, 30]
                ),
            ),
        ]
    )(10, 20),
)
def test_feature_embedder(config):
    out_shape = config["shape"][:-1] + (
        sum(config["kwargs"]["embedding_dims"]),
    )
    embed_feature = FeatureEmbedder(
        **config["kwargs"]
    )
    for embed in embed_feature._FeatureEmbedder__embedders:
        nn.init.constant_(embed.weight, 1.0)

    def test_parameters_length():
        exp_params_len = len([p for p in embed_feature.parameters()])
        act_params_len = len(config["kwargs"]["embedding_dims"])
        assert exp_params_len == act_params_len
    
    def test_forward_pass():
        act_output = embed_feature(torch.ones(config["shape"]).to(torch.long))
        exp_output = torch.ones(out_shape)
        
        assert act_output.shape == exp_output.shape
        assert torch.abs(torch.sum(act_output - exp_output)) < 1e-20

    test_parameters_length()
    test_forward_pass()

@pytest.mark.parametrize(
    "config",
    (
        lambda N, T: [
            dict(
                N=N,
                T=T,
                static_cat=dict(C=2),
                static_real=dict(C=5),
                dynamic_cat=dict(C=3),
                dynamic_real=dict(C=4),
                embed_static=dict(
                    cardinalities=[2, 4],
                    embedding_dims=[3, 6],
                ),
                embed_dynamic=dict(
                    cardinalities=[30, 30, 30],
                    embedding_dims=[10, 20, 30],
                ),
            )
        ]
    )(10, 25),
)
def test_feature_assembler(config):
    # iterate over the power-set of all possible feature types, excluding the empty set
    feature_types = {
        "static_cat",
        "static_real",
        "dynamic_cat",
        "dynamic_real",
    }
    feature_combs = chain.from_iterable(
        combinations(feature_types, r)
        for r in range(1, len(feature_types) + 1)
    )

    # iterate over the power-set of all possible feature types, including the empty set
    embedder_types = {"embed_static", "embed_dynamic"}
    embedder_combs = chain.from_iterable(
        combinations(embedder_types, r)
        for r in range(0, len(embedder_types) + 1)
    )
    
    for enabled_embedders in embedder_combs:
        embed_static = (
            FeatureEmbedder(**config["embed_static"])
            if "embed_static" in enabled_embedders
            else None
        )
        embed_dynamic = (
            FeatureEmbedder(**config["embed_dynamic"])
            if "embed_dynamic" in enabled_embedders
            else None
        )

        for enabled_features in feature_combs:
            assemble_feature = FeatureAssembler(
                T=config["T"],
                embed_static=embed_static,
                embed_dynamic=embed_dynamic,
            )
            # assemble_feature.collect_params().initialize(mx.initializer.One())


            def test_parameters_length():
                exp_params_len = sum(
                    [
                        len(config[k]["embedding_dims"])
                        for k in ["embed_static", "embed_dynamic"]
                        if k in enabled_embedders
                    ]
                )
                act_params_len = len([p for p in assemble_feature.parameters()])
                assert exp_params_len == act_params_len

            test_parameters_length()
