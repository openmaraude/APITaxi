AjaxGraph = Rickshaw.Class.create(Rickshaw.Graph.Ajax, {
    initialize: function(args) {
        main_container = $("#main_chart_container");
        container_id = "chart_container_" + args.zupc_insee;
    main_container.append("<div class='chart_container' id='" + container_id + "'></div>");
        container = $('#'+container_id);
        nb_id = 'nb_' + args.zupc_insee;
        chart_id = 'chart_' + args.zupc_insee;
        container.append("<div class='row_chart'><div class='phantom_chart'></div><div class='ville_chart'>" + args.zupc_name + "</div></div>");
        container.append("<div class='nb_taxis' id='" + nb_id + "'></div>");
        container.append("<div class='chart' id='" + chart_id + "'></div>");
        args.element = document.getElementById(chart_id);
        this.element_nb_taxis = $('#'+nb_id);
        args.width = 235;
        args.height = 85;
        this.args = args; // pass through to Rickshaw.Graph

        this.onError = args.onError || function() {};
        this.request();
    },
    onComplete: function(transport) {
        var graph = transport.graph;
        var axes = new Rickshaw.Graph.Axis.Time({graph: graph,
            ticksTreatment: 'glow',
        });
        graph.render();
    },
    onData: function(d) {
        nb_taxis = 0;
        if (d.data.length > 0) {
            nb_taxis = d.data[d.data.length-1]['y'];
        }
        this.element_nb_taxis.text(nb_taxis);
        return [{name: "taxis", data: d.data}]; 
    },
    beforeSend: function(request) {
        request.setRequestHeader("X-VERSION", 2);
        request.setRequestHeader("X-API-KEY", this.args.apikey);
    },
    request: function() {
        var url = this.args.dataURL;
        if (this.args.zupc_insee != "0") {
            url += '?zupc=' + this.args.zupc_insee;
        }
        jQuery.ajax({
            url: url,
            dataType: 'json',
            success: this.success.bind(this),
            error: this.error.bind(this),
            beforeSend: this.beforeSend.bind(this)
        });
    },
    renderer: 'area'
});
