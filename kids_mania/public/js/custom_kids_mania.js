function set_shortcut_colors () {
    if ( cur_page ) {
        if ( cur_page.page.label == "Workspaces" ) {
            frappe.run_serially( [
                () => frappe.timeout( 3 ),
                () => {
                    frappe.call( {
                        method: 'kids_mania.main.get_workspace_shortcut_labels',
                        args: {
                            workspace_name: frappe.workspace.page.title,
                        },
                        callback: function ( r ) {
                            var result = r.message;
                            $( ".shortcut-widget-box" ).each( function ( index ) {
                                let row_name = $( this ).attr( "data-widget-name" )
                                let colors = result[ row_name ]
                                if ( colors ) {
                                    if ( colors.bg_color ) {
                                        $( this ).css( "background-color", colors.bg_color )
                                    }
                                    if ( colors.color ) {
                                        $( this ).find( '.widget-title' ).css( "color", colors.color )
                                    }
                                }
                            } );
                        }
                    } );
                }
            ] );
        }
    }
}


$( document ).ready( function () {
    set_shortcut_colors()
    navigation.addEventListener( 'navigate', () => {
        set_shortcut_colors()
    } );
} )

