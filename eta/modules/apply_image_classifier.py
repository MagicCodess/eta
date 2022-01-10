#!/usr/bin/env python
"""
A module that uses an `eta.core.learning.ImageClassifier` to classify images
or the frames of videos.

Info:
    type: eta.core.types.Module
    version: 0.1.0

Copyright 2017-2022, Voxel51, Inc.
voxel51.com
"""
# pragma pylint: disable=redefined-builtin
# pragma pylint: disable=unused-wildcard-import
# pragma pylint: disable=wildcard-import
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from builtins import *

# pragma pylint: enable=redefined-builtin
# pragma pylint: enable=unused-wildcard-import
# pragma pylint: enable=wildcard-import

import logging
import os
import sys

from eta.core.config import Config, ConfigError
import eta.core.datasets as etad
import eta.core.image as etai
import eta.core.features as etaf
import eta.core.learning as etal
import eta.core.module as etam
import eta.core.utils as etau
import eta.core.video as etav


logger = logging.getLogger(__name__)


class ModuleConfig(etam.BaseModuleConfig):
    """Module configuration settings.

    Attributes:
        data (DataConfig)
        parameters (ParametersConfig)
    """

    def __init__(self, d):
        super(ModuleConfig, self).__init__(d)
        self.data = self.parse_object_array(d, "data", DataConfig)
        self.parameters = self.parse_object(d, "parameters", ParametersConfig)


class DataConfig(Config):
    """Data configuration settings.

    Inputs:
        video_path (eta.core.types.Video): [None] the input video
        input_labels_path (eta.core.types.VideoLabels): [None] an optional
            input VideoLabels file to which to add the predictions generated by
            processing `video_path`
        image_path (eta.core.types.Image): [None] the input image
        input_image_labels_path (eta.core.types.ImageLabels): [None] an
            optional input ImageLabels files to which to add the predictions
            generated by processing `image_path`
        images_dir (eta.core.types.ImageFileDirectory): [None] an input
            directory of images
        image_dataset_path (eta.core.types.LabeledDatasetIndex): [None] a
            manifest for an eta.core.datasets.LabeledImageDataset
        input_image_set_labels_path (eta.core.types.ImageSetLabels): [None] an
            optional input ImageSetLabels file to which to add the predictions
            generated by processing `images_dir`

    Outputs:
        output_labels_path (eta.core.types.VideoLabels): [None] a VideoLabels
            file containing the predictions generated by processing
            `video_path`
        video_features_dir (eta.core.types.VideoFramesFeaturesDirectory):
            [None] a directory in which to write features for the frames of
            `video_path`. If provided, the classifier used must support
            generating features
        output_image_labels_path (eta.core.types.ImageLabels): [None] an
            ImageLabels file containing the predictions generated by
            processing `image_path`
        image_features (eta.core.types.ImageFeature): [None] a path to which to
            write the features for `image_path`. If provided, the classifier
            used must support generating features
        output_image_set_labels_path (eta.core.types.ImageSetLabels): [None] an
            ImageSetLabels file containing the predictions generated by
            processing `images_dir` or `image_dataset_path`
        image_set_features_dir (eta.core.types.ImageSetFeaturesDirectory):
            [None] a directory in which to write features for the images in
            `images_dir`. If provided, the classifier used must support
            generating features
    """

    def __init__(self, d):
        # Single video
        self.video_path = self.parse_string(d, "video_path", default=None)
        self.input_labels_path = self.parse_string(
            d, "input_labels_path", default=None
        )
        self.output_labels_path = self.parse_string(
            d, "output_labels_path", default=None
        )
        self.video_features_dir = self.parse_string(
            d, "video_features_dir", default=None
        )

        # Single image
        self.image_path = self.parse_string(d, "image_path", default=None)
        self.input_image_labels_path = self.parse_string(
            d, "input_image_labels_path", default=None
        )
        self.output_image_labels_path = self.parse_string(
            d, "output_image_labels_path", default=None
        )
        self.image_features = self.parse_string(
            d, "image_features", default=None
        )

        # Directory of images
        self.images_dir = self.parse_string(d, "images_dir", default=None)
        self.input_image_set_labels_path = self.parse_string(
            d, "input_image_set_labels_path", default=None
        )
        self.output_image_set_labels_path = self.parse_string(
            d, "output_image_set_labels_path", default=None
        )
        self.image_set_features_dir = self.parse_string(
            d, "image_set_features_dir", default=None
        )
        self.image_dataset_path = self.parse_string(
            d, "image_dataset_path", default=None
        )

        self._validate()

    def _validate(self):
        if self.video_path:
            if not self.output_labels_path:
                raise ConfigError(
                    "`output_labels_path` is required when `video_path` is "
                    "set"
                )

        if self.image_path:
            if not self.output_image_labels_path:
                raise ConfigError(
                    "`output_image_labels_path` is required when `image_path` "
                    "is set"
                )

        if self.images_dir:
            if not self.output_image_set_labels_path:
                raise ConfigError(
                    "`output_image_set_labels_path` is required when "
                    "`images_dir` is set"
                )

        if self.image_dataset_path:
            if not self.output_image_set_labels_path:
                raise ConfigError(
                    "`output_image_set_labels_path` is required when "
                    "`image_dataset_path` is set"
                )

        if self.images_dir and self.image_dataset_path:
            raise ConfigError(
                "Only one of `images_dir`, `image_dataset_path` may be "
                "specified"
            )


class ParametersConfig(Config):
    """Parameter configuration settings.

    Parameters:
        classifier (eta.core.types.ImageClassifier): an
            `eta.core.learning.ImageClassifierConfig` describing the
            `eta.core.learning.ImageClassifier` to use
        confidence_threshold (eta.core.types.Number): [None] a confidence
            threshold to use when assigning labels
        record_top_k_probs (eta.core.types.Number): [None] the number of top-k
            class probabilities to record for the predictions
    """

    def __init__(self, d):
        self.classifier = self.parse_object(
            d, "classifier", etal.ImageClassifierConfig
        )
        self.confidence_threshold = self.parse_number(
            d, "confidence_threshold", default=None
        )
        self.record_top_k_probs = self.parse_number(
            d, "record_top_k_probs", default=None
        )


def _build_attribute_filter(threshold):
    if threshold is None:
        logger.info("Predicting all attributes")
        return lambda attrs: attrs

    logger.info("Returning predictions with confidence >= %f", threshold)
    attr_filters = [
        lambda attr: attr.confidence is None
        or attr.confidence > float(threshold)
    ]
    return lambda attrs: attrs.get_matches(attr_filters)


def _apply_image_classifier(config):
    # Build classifier
    classifier = config.parameters.classifier.build()
    logger.info("Loaded classifier %s", type(classifier))

    record_top_k_probs = config.parameters.record_top_k_probs
    if record_top_k_probs:
        etal.ExposesProbabilities.ensure_exposes_probabilities(classifier)

    # Build attribute filter
    attr_filter = _build_attribute_filter(
        config.parameters.confidence_threshold
    )

    # Process data
    with classifier:
        for data in config.data:
            if data.video_path:
                logger.info("Processing video '%s'", data.video_path)
                _process_video(
                    data, classifier, attr_filter, record_top_k_probs
                )
            if data.image_path:
                logger.info("Processing image '%s'", data.image_path)
                _process_image(
                    data, classifier, attr_filter, record_top_k_probs
                )
            if data.images_dir:
                logger.info("Processing image directory '%s'", data.images_dir)
                _process_images_dir(
                    data, classifier, attr_filter, record_top_k_probs
                )
            if data.image_dataset_path:
                logger.info(
                    "Processing image dataset '%s'", data.image_dataset_path
                )
                _process_image_dataset(
                    data, classifier, attr_filter, record_top_k_probs
                )


def _process_video(data, classifier, attr_filter, record_top_k_probs):
    write_features = data.video_features_dir is not None

    if write_features:
        etal.ExposesFeatures.ensure_exposes_features(classifier)
        features_handler = etaf.VideoFramesFeaturesHandler(
            data.video_features_dir
        )

    if data.input_labels_path:
        logger.info(
            "Reading existing labels from '%s'", data.input_labels_path
        )
        video_labels = etav.VideoLabels.from_json(data.input_labels_path)
    else:
        video_labels = etav.VideoLabels()

    # Classify frames of video
    with etav.FFmpegVideoReader(data.video_path) as vr:
        for img in vr:
            logger.debug("Processing frame %d", vr.frame_number)

            # Classify frame
            attrs = _classify_image(
                img, classifier, attr_filter, record_top_k_probs
            )

            # Write features, if necessary
            if write_features:
                fvec = classifier.get_features()
                features_handler.write_feature(fvec, vr.frame_number)

            # Record predictions
            video_labels.add_frame_attributes(attrs, vr.frame_number)

    logger.info("Writing labels to '%s'", data.output_labels_path)
    video_labels.write_json(data.output_labels_path)


def _process_image(data, classifier, attr_filter, record_top_k_probs):
    write_features = data.image_features is not None

    if write_features:
        etal.ExposesFeatures.ensure_exposes_features(classifier)
        features_handler = etaf.ImageFeaturesHandler()

    if data.input_image_labels_path:
        logger.info(
            "Reading existing labels from '%s'", data.input_image_labels_path
        )
        image_labels = etai.ImageLabels.from_json(data.input_image_labels_path)
    else:
        image_labels = etai.ImageLabels()

    # Classsify image
    img = etai.read(data.image_path)
    attrs = _classify_image(img, classifier, attr_filter, record_top_k_probs)

    # Write features, if necessary
    if write_features:
        fvec = classifier.get_features()
        features_handler.write_feature(fvec, data.image_features)

    # Record predictions
    image_labels.add_attributes(attrs)

    logger.info("Writing labels to '%s'", data.output_image_labels_path)
    image_labels.write_json(data.output_image_labels_path)


def _process_images_dir(data, classifier, attr_filter, record_top_k_probs):
    # get paths to all images in directory
    filenames = etau.list_files(data.images_dir)
    inpaths = [os.path.join(data.images_dir, fn) for fn in filenames]

    _process_image_path_list(
        data, classifier, attr_filter, record_top_k_probs, inpaths
    )


def _process_image_dataset(data, classifier, attr_filter, record_top_k_probs):
    # get paths to all images in dataset
    dataset = etad.LabeledImageDataset(data.image_dataset_path)
    inpaths = list(dataset.iter_data_paths())

    _process_image_path_list(
        data, classifier, attr_filter, record_top_k_probs, inpaths
    )


def _process_image_path_list(
    data, classifier, attr_filter, record_top_k_probs, inpaths
):
    write_features = data.image_set_features_dir is not None

    if write_features:
        etal.ExposesFeatures.ensure_exposes_features(classifier)
        features_handler = etaf.ImageSetFeaturesHandler(
            data.image_set_features_dir
        )

    if data.input_image_set_labels_path:
        logger.info(
            "Reading existing labels from '%s'",
            data.input_image_set_labels_path,
        )
        image_set_labels = etai.ImageSetLabels.from_json(
            data.input_image_set_labels_path
        )
    else:
        image_set_labels = etai.ImageSetLabels()

    # Classify images in directory
    for inpath in inpaths:
        logger.info("Processing image '%s'", inpath)
        filename = os.path.basename(inpath)

        # Classify image
        img = etai.read(inpath)
        attrs = _classify_image(
            img, classifier, attr_filter, record_top_k_probs
        )

        # Write features, if necessary
        if write_features:
            fvec = classifier.get_features()
            features_handler.write_feature(fvec, filename)

        # Record predictions
        image_set_labels[filename].add_attributes(attrs)

    logger.info("Writing labels to '%s'", data.output_image_set_labels_path)
    image_set_labels.write_json(data.output_image_set_labels_path)


def _classify_image(img, classifier, attr_filter, record_top_k_probs):
    # Perform prediction
    attrs = classifier.predict(img)

    # Record top-k classes, if necessary
    if record_top_k_probs:
        all_top_k_probs = classifier.get_top_k_classes(record_top_k_probs)
        for attr, top_k_probs in zip(attrs, all_top_k_probs.flatten()):
            attr.top_k_probs = top_k_probs

    # Filter predictions
    attrs = attr_filter(attrs)

    return attrs


def run(config_path, pipeline_config_path=None):
    """Run the apply_image_classifier module.

    Args:
        config_path: path to a ModuleConfig file
        pipeline_config_path: optional path to a PipelineConfig file
    """
    config = ModuleConfig.from_json(config_path)
    etam.setup(config, pipeline_config_path=pipeline_config_path)
    _apply_image_classifier(config)


if __name__ == "__main__":
    run(*sys.argv[1:])  # pylint: disable=no-value-for-parameter
