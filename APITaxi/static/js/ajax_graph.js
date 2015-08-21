AjaxGraph = Rickshaw.Class.create(Rickshaw.Graph.Ajax, {
    initialize: function(args) {
        this.apikey = args.apikey;

        this.dataURL = args.dataURL;
        this.onData = args.onData || function(d) { return d };
        this.onComplete = args.onComplete || function() {};
        this.onError = args.onError || function() {};
        this.args = args; // pass through to Rickshaw.Graph
        this.request();
    },
    beforeSend: function(request) {
        request.setRequestHeader("X-VERSION", 2);
        request.setRequestHeader("X-API-KEY", this.apikey);
    },
    request: function() {
        jQuery.ajax({
            url: this.dataURL,
            dataType: 'json',
            success: this.success.bind(this),
            error: this.error.bind(this),
            beforeSend: this.beforeSend.bind(this)
        });
    }
});
