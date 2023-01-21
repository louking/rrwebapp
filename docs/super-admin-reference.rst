*******************************************
Super Admin Reference
*******************************************

This page gives a reference to all **scoretility** views which are available to
:term:`users <user>` who have the :term:`super admin` :term:`security role`.


.. _Age Grade Tables view:

Age Grade Tables view
=======================
**Navigation:** Super > Age Grade Tables

This view defines what age grade tables are available, and allows import of the age grade factors

    :Table Name:
        name for age grade table
    
    :Last Update:
        (readonly) date/time when the last update was made to this age grade table
    
In addition to the **New**, **Edit**, **Delete** buttons, there is the following action button.

    :Import Factors:
        use this to import age grade factors associated with **Gender** and **Type**. The factors
        must be in the format as seen in https://github.com/AlanLyttonJones/Age-Grade-Tables/tree/master/2020%20Files.

        .. note::
            **Gender** and **Type** must be specified when importing a file

        .. note::
            While there is a **Clear** button on this form, there is no general use for it. Factors
            are overwritten when inported.

.. image:: images/age-grade-tables-view.*
    :align: center
    
.. image:: images/age-grade-tables-import.*
    :align: center


.. _Clubs view:

Clubs view
=======================
**Navigation:** Super > Clubs

Many operations are achieved within a :term:`club`, via the pulldown near the top of each view. This view defines
what clubs are available.

    :Short Name (slug):
        short name for the club which is displayed on the relevant views
    
    :Long Name:
        official name for the club
    
    :Location:
        location of the club, in a form suitable for lookup using Google Maps
    
    :Service:
        if the club member data can be downloaded, the service must be specified. Currently
        this must be blank or "runsignup"
    
    :Service ID:
        id of club as known by the service
    
    :Age Grade Table:
        the age grade table defined on :ref:`Age Grade Tables view` to use for age grade
        calculations

.. image:: images/clubs-view.*
    :align: center
    
.. image:: images/clubs-edit.*
    :align: center


.. _Service Credentials view:

Service Credentials view
==========================
**Navigation:** Super > Service Credentials

This view defines the credentials used to access services used by **scoretility**

    :Service Name:
        name of the service

    :Key:
        key to be used to access the service
    
    :Secret:
        secret to be used in conjunction with **Key** to access the service
    
.. image:: images/service-credentials-view.*
    :align: center
    
.. image:: images/service-credentials-edit.*
    :align: center


.. _Users view:

Users view
=======================
**Navigation:** Super > Users

This view defines the :term:`users <user>` which can administrate **scoretility**

    :Name:
        name of the user
    
    :Email:
        email address for the user
    
    :Password:
        can be used to define the user's email address, but generally should be left
        blank as the user should define their own password 

    :Owner:
        checkbox for administrators who have **Owner** access
    
    :Club:
        used to select the club for which **Admin** and **Viewer** access is being given

    :Admin:
        check to give read / write access for the indicated **Club**

    :Viewer:
        check to give read access for the indicated **Club**

.. note::
    when editing a :term:`user`, give **Admin** / **Viewer** access for each **Club** that the user should be able
    to access before clicking **Update**

.. image:: images/users-view.*
    :align: center
    
.. image:: images/users-edit.*
    :align: center
