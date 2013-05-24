define(['exports', 'jquery', 'underscore', 'base', 'table_sorter', 'table_filter',
    'text!templates/sort_filter_table.html',
    'text!templates/experiments/item.html',
    'text!templates/experiments/row.html',
     'text!templates/experiments/document.html'],
function experiments(exports, $, _, base, table_sorter, table_filter, home_template, item_template, row_template, document_template) {

    exports.experiment_factory = function experiment_factory(attrs, options) {
        var new_obj = new base.Model(attrs, options);
        new_obj.url = '/experiments/' + options.route_args[0];
        return new_obj;
    };

    exports.Experiment = base.Model.extend({
        urlRoot: '/experiments/',
        initialize: function initialize(attrs, options) {
            if (options && options.route_args) {
                this.id = options.route_args[0];
                this.deferred = this.fetch();
            }
        }
    });

    exports.ExperimentCollection = base.Collection.extend({
        model: exports.Experiment,
        url: '/experiments/'
    });

    // The experiments home screen
    var experimentHomeView = base.TableView.extend({
        template: _.template(home_template),
        row_template: _.template(row_template),
        table_header: [ 'Accession',
                        'Assay Type',
                        'Target',
                        'Biosample',
                        'Biological Replicates',
                        'Files',
                        'Lab',
                        'Project'
                        ],
        sort_initial: 1
    },
    {
        route_name: 'experiments',
        model_factory: exports.ExperimentCollection
    });

    exports.DocumentView = base.View.extend({
        tagName: 'section',
        attributes: {'class': 'type-document view-detail panel'},
        initialize: function initialize(options) {
            var model = options.model;
            this.deferred = model.deferred;
        },
        template: _.template(document_template)
    });

    var ExperimentView = exports.ExperimentView = base.View.extend({
        document: exports.DocumentView,
        initialize: function initialize(options) {
            var model = options.model,
                deferred = $.Deferred();
            this.deferred = deferred;
            model.deferred = model.fetch();
            $.when(model.deferred).done(_.bind(function () {
                if(model.links.replicates.length) {
                    this.documents = _.map(model.links.replicates[0].links.library.links.documents, _.bind(function (item) {
                        item.deferred = item.fetch();
                        var subview = new this.document({model: item});
                        $.when(subview.deferred).then(function () {
                            subview.render();
                        });
                        return subview;
                    }, this));
                }
                $.when.apply($, _.pluck(this.documents, 'deferred')).then(function () {
                    deferred.resolve();
                });
            }, this));
        },
        template: _.template(item_template),
        render: function render() {
            ExperimentView.__super__.render.apply(this, arguments);
            if(this.documents) {
                var div = this.$el.find('div.protocols');
                if(this.documents.length) div.before('<h3>Protocols</h3>');
                _.each(this.documents, function (view) {
                    div.append(view.el);
                });
            }
            return this;
        }
    }, {
        route_name: 'experiment',
        model_factory: exports.experiment_factory
    });

    var experimentAddOverlay = exports.experimentAddOverlay = base.Modal.extend({
        tagName: 'form',
        events: {'submit': 'submit'},
        className: base.Modal.prototype.className + ' form-horizontal',
        initialize: function initialize(options) {
            var name = options.route_args[0];
            this.action = _.find(this.model._links.actions, function(item) {
                return item.name === name;
            });
            this.title = this.action.title;
            this.deferred = $.get(this.action.profile);
            this.deferred.done(_.bind(function (data) {
                this.schema = data;
            }, this));
        },
        render: function render() {
            experimentAddOverlay.__super__.render.apply(this, arguments);
            this.form = this.$('.modal-body').jsonForm({
                schema: this.schema,
                form: _.without(_.keys(this.schema.properties), ''),
                submitEvent: false,
                onSubmitValid: _.bind(this.send, this)
            });

            setTimeout(function() {
                $(document).ready(function(){
                    // Populating labs using user details 
                    var assayId = document.getElementsByName("assay_type")[0].id;
                    $("#"+ assayId).chosen();
                    var id = document.getElementsByName("lab_uuid")[0].id;
                    $("#" + id).chosen();
                    var awardId = document.getElementsByName("award_uuid")[0].id;
                    $("#"+ awardId).chosen();
                    $.ajax({
                        async: false,
                        url: "/current-user",
                        dataType: "json",
                        success:  function(user) {
                            var labs = user['_links']['labs'];
                            _.each(labs, function(lab) {
                                var labId = lab['href'].substr(lab['href'].length - 36);
                                $.ajax({
                                    async: false,
                                    url: "/get_data",
                                    dataType: "json",
                                    data: {collection: 'lab', id: labId},
                                    success:  function(labs) {
                                        _.each(labs, function(value, key) {
                                            $("#" + id).append('<option value = ' + key + '>' + value + '</option>');
                                        });
                                    }
                                });
                                $.ajax({
                                    async: false,
                                    url: "/get_data",
                                    dataType: "json",
                                    data: {collection: 'award', id: labId},
                                    success:  function(awards) {
                                        _.each(awards, function(value, key) {
                                            $("#" + awardId).append('<option value = ' + key + '>' + value + '</option>');
                                        });
                                   }
                                });
                            });
                        }
                    });
                    $("#"+ id).trigger('liszt:updated');
                    $("#"+ awardId).trigger('liszt:updated');
                });
            }, 1);
            return this;
        },
        submit: function submit(evt) {
            this.form.submit(evt);
        },
        send: function send(value)  {
            this.value = value;
            var accession_uuid;
            $.ajax({
                async: false,
                url: "/generate_accession",
                dataType: "json",
                success:  function(accession) {
                   accession_uuid = accession;
                }
            });
            this.value.dataset_accession  = accession_uuid;
            var submitter;
            $.ajax({
                async: false,
                url: "/current-user",
                dataType: "json",
                success:  function(user) {
                   submitter = (user['_links']['self']['href']).substr((user['_links']['self']['href']).length - 36);
                }
            });
            this.value.submitter_uuid = submitter;
            this.model.sync(null, this.model, {
                url: this.action.href,
                type: this.action.method,
                contentType: 'application/json',
                data: JSON.stringify(value),
                dataType: 'json'
            }).done(_.bind(function (data) {
                // close, refresh
                console.log(data);
                var url = data._links.items[0].href;
                // force a refresh
                app.view_registry.history.path = null;
                app.view_registry.history.navigate(url, {trigger: true});
            }, this)).fail(_.bind(function (data) {
                // flag errors, try again
                console.log(data);
            }, this));
            // Stop event propogation
            return false;
        }
    }, {
        route_name: 'add-experiment',
        model_factory: function model_factory(attrs, options) {
            return app.view_registry.current_views.content.model;
        }
    });
    return exports;
});