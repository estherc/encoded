/** @jsx React.DOM */
define(['exports', 'react', 'globals', 'jsx!home'],
function (errors, React, globals, home) {
    'use strict';

    var SignIn = home.SignIn;


    var Error = errors.Error = React.createClass({
        render: function() {
            var context = this.props.context;
            var itemClass = globals.itemClass(context, 'panel-gray');
            return (
                <div class={itemClass}>
                    <h1>{context.title}</h1>
                    <p>{context.description}</p>
                </div>
            );
        }
    });

    globals.content_views.register(Error, 'error');


    var LoginDenied = errors.LoginDenied = React.createClass({
        render: function() {
            var context = this.props.context;
            var itemClass = globals.itemClass(context, 'panel-gray');
            return (
                <div class={itemClass}>
                    <div class="row">
                        <div class="span7">
                            <h1>Login failure</h1>
                            <p>Access is restricted to ENCODE consortium members.
                                <a href='mailto:encode-help@lists.stanford.edu'>Request an account</a>
                            </p>
                        </div>
                        <SignIn session={this.props.session} />
                    </div>
                </div>
            );
        }
    });

    globals.content_views.register(LoginDenied, 'LoginDenied');


    return errors;
});
